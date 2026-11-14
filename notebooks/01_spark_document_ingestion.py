# Databricks notebook source
# MAGIC %md
# MAGIC # AI Data Engineering: PySpark document ingestion and provenance
# MAGIC Synthetic technical documents only. No Azure OpenAI, embeddings API or
# MAGIC private documents. Run on Databricks Free Edition serverless.

# COMMAND ----------
from pyspark.sql import functions as F

SCHEMA_NAME = "rag_portfolio"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
spark.sql(f"USE SCHEMA {SCHEMA_NAME}")
documents = [
    ("architecture", "public", "lakehouse", "Delta Lake enables ACID transactions. Bronze captures raw events. Silver validates records."),
    ("streaming", "public", "streaming", "Kafka consumers read partitioned events. Checkpoints protect Structured Streaming recovery."),
    ("retrieval", "public", "ai", "Hybrid retrieval combines lexical and vector rankings. Citations identify the source document."),
    ("restricted", "internal", "security", "Key Vault manages sensitive service secrets. Access controls restrict internal material."),
]
bronze = spark.createDataFrame(
    documents, ["doc_id", "access_group", "source", "text"]
).withColumn("document_sha256", F.sha2("text", 256))
assert bronze.select("doc_id").distinct().count() == bronze.count()
bronze.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("bronze_documents")

# COMMAND ----------
# Sentence-sized demo chunks. Production requires token-aware chunking and versioning.
chunks = (
    bronze.select("doc_id", "access_group", "source", "document_sha256",
        F.posexplode(F.split("text", r"\.")).alias("chunk_index", "text"))
    .withColumn("text", F.trim("text"))
    .filter(F.length("text") > 0)
    .withColumn("chunk_id", F.concat_ws(":", F.col("doc_id"), F.col("chunk_index")))
    .withColumn("chunk_sha256", F.sha2("text", 256))
    .select("chunk_id", "doc_id", "source", "access_group",
            "text", "document_sha256", "chunk_sha256")
)
chunks.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_chunks")
assert spark.table("bronze_documents").count() == 4
assert spark.table("silver_chunks").count() == 9
assert spark.table("silver_chunks").filter("access_group = 'internal'").count() == 2
print("PASS: 4 synthetic source documents, 9 traceable chunks")
display(spark.table("silver_chunks").select("chunk_id", "source", "access_group", "text"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Security boundary
# MAGIC Access groups here are synthetic labels, not an authentication system.
# MAGIC The calling service must enforce identity and group permissions before
# MAGIC production retrieval. Do not index confidential or regulated files in this demo.
