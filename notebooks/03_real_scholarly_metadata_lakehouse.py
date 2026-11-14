# Databricks notebook source
# MAGIC %md
# MAGIC # Scholarly metadata index: OpenAlex + Crossref, real public records
# MAGIC Source records contain titles, DOIs, years and citation metadata ONLY;
# MAGIC no publisher abstracts, paywalled PDFs or copyrighted document bodies.
# MAGIC Run fetch_research_catalogues.py first, then upload its two output
# MAGIC folders to a private UC Volume; never commit API keys to notebooks.

# COMMAND ----------
from pyspark.sql import functions as F, Window
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType

dbutils.widgets.text("landing_root", "")
landing = dbutils.widgets.get("landing_root").rstrip("/")
if not landing.startswith("/Volumes/"):
    raise ValueError("Set landing_root to /Volumes/<catalog>/<schema>/<volume>/research")
spark.sql("CREATE SCHEMA IF NOT EXISTS research_public")
spark.sql("USE SCHEMA research_public")

# COMMAND ----------
schema = StructType([
    StructField("record_id", StringType()), StructField("source", StringType()),
    StructField("doi", StringType()), StructField("title", StringType()),
    StructField("year", IntegerType()), StructField("citation_count", LongType()),
    StructField("landing_url", StringType()), StructField("text_for_index", StringType()),
    StructField("copyright_scope", StringType())
])
alex = spark.read.schema(schema).json(f"{landing}/openalex/*.jsonl")
crossref = spark.read.schema(schema).json(f"{landing}/crossref/*.jsonl")
raw = alex.unionByName(crossref)
assert raw.limit(1).count() == 1, "No public scholarly metadata files uploaded"
raw.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("bronze_scholarly_works")

# COMMAND ----------
reason = F.concat_ws("; ",
    F.when(F.col("doi").isNull() | (F.length(F.trim("doi")) == 0), "missing DOI"),
    F.when(F.col("title").isNull() | (F.length(F.trim("title")) == 0), "missing title"),
    F.when(~F.col("source").isin("OpenAlex", "Crossref"), "unknown provenance"))
tagged = raw.withColumn("quality_issue", reason)
bad = tagged.filter(F.length("quality_issue") > 0)
valid = tagged.filter(F.length("quality_issue") == 0)
bad.select("record_id", "source", "quality_issue").write.format("delta").mode(
    "overwrite").option("overwriteSchema", "true").saveAsTable("silver_quarantine")

# Prefer OpenAlex metadata for duplicate DOIs. Never treat this as an
# authoritative bibliographic resolution if the two catalogs disagree.
priority = Window.partitionBy("doi").orderBy(
    F.when(F.col("source") == "OpenAlex", 0).otherwise(1),
    F.col("citation_count").desc_nulls_last(), F.col("record_id"))
deduped = (valid.withColumn("rn", F.row_number().over(priority))
           .filter("rn = 1").drop("rn"))
deduped.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_unique_works")

# COMMAND ----------
tokens = (deduped.select("doi", "year", "source", "title",
            F.explode(F.split(
                F.regexp_replace(F.lower("text_for_index"), "[^a-z0-9]+", " "), " ")).alias("token"))
    .filter(F.length("token") >= 3)
    .dropDuplicates(["doi", "token"]))
tokens.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_term_index")

yearly = deduped.groupBy("year", "source").agg(
    F.count("*").alias("works"),
    F.sum(F.coalesce("citation_count", F.lit(0))).alias("total_citations"))
topics = tokens.groupBy("token").agg(
    F.countDistinct("doi").alias("document_frequency")).orderBy(
        F.col("document_frequency").desc())
yearly.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold_works_by_year")
topics.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold_index_terms")

# COMMAND ----------
assert deduped.groupBy("doi").count().filter("count > 1").count() == 0
assert raw.count() == bad.count() + valid.count()
assert tokens.select("doi").distinct().count() <= deduped.count()
print("PASS: source-to-Gold scholarly metadata, DOI reconciliation, index quality")
display(topics.limit(25))
display(yearly.orderBy("year", "source").limit(25))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Next production-grade step
# MAGIC Implement a vector index on **licensed** open-access text with per-document
# MAGIC license checks, source-based ACLs, source update/deletion handling,
# MAGIC embeddings versioning, chunk evaluation and retrieval benchmark suites.
# MAGIC Title/DOI search is metadata retrieval, not full-text RAG.
