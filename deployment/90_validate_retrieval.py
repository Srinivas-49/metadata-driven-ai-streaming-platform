# Databricks notebook source
# MAGIC %md
# MAGIC # Retrieval quality gate — grounded synthetic evaluation
# MAGIC Run only after ingestion and retrieval-evaluation notebooks.

# COMMAND ----------
from pyspark.sql import functions as F
spark.sql("USE SCHEMA rag_portfolio")
expected = {
    "bronze_documents": 4,
    "silver_chunks": 9,
    "gold_retrieval_evaluation": 5,
}
for name, expected_count in expected.items():
    count = spark.table(name).count()
    assert count == expected_count, f"{name}: expected {expected_count}, got {count}"

chunks = spark.table("silver_chunks")
assert chunks.groupBy("chunk_id").count().filter("count > 1").count() == 0
assert chunks.filter("document_sha256 IS NULL OR chunk_sha256 IS NULL").count() == 0
eval_df = spark.table("gold_retrieval_evaluation")
assert eval_df.filter("unauthorized_result = true").count() == 0
assert eval_df.filter("false_positive = true").count() == 0
assert eval_df.filter("expected_doc IS NOT NULL AND reciprocal_rank = 0").count() == 0

# Persist only successful checks, not any source document content.
rows = [(name, count) for name, count in expected.items()]
audit = (spark.createDataFrame(rows, "metric string, measured long")
         .withColumn("checked_at", F.current_timestamp())
         .withColumn("result", F.lit("passed"))
         .select("checked_at", "metric", "measured", "result"))
audit.write.format("delta").mode("append").saveAsTable("ops_quality_audit")
print("PASS: ingestion provenance, uniqueness, access scope and retrieval evaluation")
display(audit)
