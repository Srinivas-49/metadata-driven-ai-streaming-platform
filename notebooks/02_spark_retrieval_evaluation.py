# Databricks notebook source
# MAGIC %md
# MAGIC # AI Data Engineering: ACL-first ranked retrieval and evaluation
# MAGIC Run notebook 01 first. Sparse lexical term frequency baseline.
# MAGIC No trained embedding model, generated answers or production authorization.

# COMMAND ----------
import re
from pyspark.sql import functions as F

spark.sql("USE SCHEMA rag_portfolio")
corpus = spark.table("silver_chunks")

# COMMAND ----------
def retrieve(question, allowed_groups, top_k=3):
    """Small-corpus lexical baseline; filter before tokenization and ranking.

    allowed_groups must be supplied by trusted caller authorization in reality.
    """
    if top_k < 1:
        raise ValueError("top_k must be positive")
    groups = sorted(set(allowed_groups))
    query_tokens = sorted(set(re.findall(r"[a-z0-9]+", question.lower())))
    if not groups or not query_tokens:
        return []
    authorized = corpus.filter(F.col("access_group").isin(groups))
    terms = (
        authorized.select("chunk_id", "doc_id", "source", "access_group", "text",
                          F.explode(F.split(
                              F.regexp_replace(F.lower("text"), "[^a-z0-9]+", " "),
                              " ")).alias("token"))
        .filter(F.length("token") > 0)
    )
    ranked = (
        terms.filter(F.col("token").isin(query_tokens))
        .groupBy("chunk_id", "doc_id", "source", "access_group", "text")
        .agg(F.count("*").alias("term_frequency"))
        .orderBy(F.col("term_frequency").desc(), F.col("chunk_id").asc())
        .limit(top_k)
    )
    return [row.asDict() for row in ranked.collect()]

# COMMAND ----------
# Verify citations, ACL isolation, negative queries and ordered retrieval.
hits = retrieve("Delta Lake transactions", {"public"})
assert hits and hits[0]["doc_id"] == "architecture", hits
assert all(item["access_group"] == "public" for item in hits)
assert retrieve("Key Vault", {"public"}) == []  # Internal-only evidence is excluded.
assert retrieve("Delta Lake", set()) == []  # Fail closed when no access.
assert retrieve("zzznotincorpus", {"public"}) == []

# COMMAND ----------
# Evaluate with explicit positive, negative and denied examples.
questions = [
    {"question": "Delta Lake ACID", "groups": ["public"], "expected_doc": "architecture"},
    {"question": "Kafka partitions", "groups": ["public"], "expected_doc": "streaming"},
    {"question": "Hybrid retrieval citations", "groups": ["public"], "expected_doc": "retrieval"},
    {"question": "Key Vault", "groups": ["public"], "expected_doc": None},
    {"question": "Delta Lake", "groups": [], "expected_doc": None},
]
evidence = []
for item in questions:
    results = retrieve(item["question"], item["groups"])
    expected = item["expected_doc"]
    rank = next((position for position, hit in enumerate(results, 1)
                 if hit["doc_id"] == expected), None) if expected else None
    evidence.append({
        "query": item["question"],
        "expected_doc": expected,
        "citation": results[0]["chunk_id"] if results else None,
        "reciprocal_rank": 1.0 / rank if rank else 0.0,
        "false_positive": expected is None and bool(results),
        "unauthorized_result": any(hit["access_group"] not in item["groups"] for hit in results)
    })

evaluation = spark.createDataFrame(evidence)
evaluation.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold_retrieval_evaluation")
assert evaluation.filter("unauthorized_result").count() == 0
assert evaluation.filter("false_positive").count() == 0
assert evaluation.filter("expected_doc IS NOT NULL AND reciprocal_rank = 0").count() == 0
print("PASS: retrieval relevance, safe abstention, authorization filter and citations")
display(spark.table("gold_retrieval_evaluation"))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Boundaries
# MAGIC This is a term-frequency baseline on a four-document synthetic dataset.
# MAGIC It is not a vector database, trained model, Azure AI Search or live LLM,
# MAGIC and evaluation scores are not transferable to real-world datasets.
