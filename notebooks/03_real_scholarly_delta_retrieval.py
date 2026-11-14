# Databricks notebook source
# MAGIC %md
# MAGIC # Real Scientific Knowledge Lakehouse: Crossref + Europe PMC
# MAGIC Two public metadata sources. The ingest script applies OPEN_ACCESS:Y for
# MAGIC Europe PMC records, but you must still inspect licence restrictions before
# MAGIC uploading/reproducing abstracts. No external API calls in this notebook.
# MAGIC Upload REAL source files to a Unity Catalog Volume from your own machine.

# COMMAND ----------
import re
from pyspark.sql import functions as F, Window

dbutils.widgets.text("landing_root", "/Volumes/YOUR_CATALOG/YOUR_SCHEMA/YOUR_VOLUME/scholarly")
dbutils.widgets.text("query", "machine learning")
dbutils.widgets.text("max_documents", "2000")
root = dbutils.widgets.get("landing_root").rstrip("/")
query = dbutils.widgets.get("query").strip().lower()
max_documents = int(dbutils.widgets.get("max_documents"))
if not root.startswith("/Volumes/") or "YOUR_" in root:
    raise ValueError("Set landing_root to the actual uploaded UC Volume")
if not 1 <= max_documents <= 100000:
    raise ValueError("max_documents must be 1..100000; start at 2000")
if not query or len(query) > 80:
    raise ValueError("Query must be short and nonempty")
spark.sql("CREATE SCHEMA IF NOT EXISTS rag_real_research")
spark.sql("USE SCHEMA rag_real_research")

# COMMAND ----------
crossref = spark.read.json(f"{root}/crossref/page_*.jsonl")
europepmc = spark.read.json(f"{root}/europepmc/page_*.jsonl")
if crossref.isEmpty() and europepmc.isEmpty():
    raise ValueError("No real records found; upload both landing folders")

crossref.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("bronze_crossref")
europepmc.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("bronze_europepmc")

# COMMAND ----------
# DOI is a globally meaningful citation key, but only for works with a DOI.
# Keep source identity so a match can be audited rather than invented.
cx = crossref.select(
    F.lower(F.trim("doi")).alias("doi"),
    F.col("title").cast("string").alias("crossref_title"),
    F.col("publisher").cast("string").alias("publisher"),
    F.col("citation_count").cast("long").alias("citation_count"),
    F.lit(True).alias("has_crossref"))
ep = europepmc.select(
    F.lower(F.trim("doi")).alias("doi"),
    F.col("title").cast("string").alias("europepmc_title"),
    F.col("abstract").cast("string").alias("abstract"),
    F.lit(True).alias("has_europepmc_oa"))
# Pages can re-observe the same DOI; avoid fan-out in the joins.
cx = cx.dropDuplicates(["doi"])
ep = ep.dropDuplicates(["doi"])
enriched = (cx.join(ep, "doi", "full_outer")
    .withColumn("title", F.coalesce("europepmc_title", "crossref_title"))
    .withColumn("citation_url", F.concat(F.lit("https://doi.org/"), F.col("doi")))
    .withColumn("data_source", F.when(F.col("has_crossref").isNotNull() & F.col("has_europepmc_oa").isNotNull(),
                                       F.lit("crossref+europepmc"))
                .when(F.col("has_crossref").isNotNull(), F.lit("crossref"))
                .otherwise(F.lit("europepmc")))
    .withColumn("document_sha256", F.sha2(F.concat_ws("|", "doi", "title",
                                                     F.coalesce("abstract", F.lit(""))), 256)))
rejected = enriched.filter(
    F.col("doi").isNull() | (F.length("doi") == 0) |
    F.col("title").isNull() | (F.length("title") == 0))
accepted = enriched.filter(
    F.col("doi").isNotNull() & (F.length("doi") > 0) &
    F.col("title").isNotNull() & (F.length("title") > 0))
rejected.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_rejected_documents")
accepted.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_doi_documents")

# COMMAND ----------
# For a Free Edition demo, limit the chunking materialisation to a manageable,
# deterministic subset. Full corpus remains in Bronze and curated Silver.
selected = accepted.orderBy("doi").limit(max_documents)
text = (selected.select(
    "doi", "title", "document_sha256", "citation_url", "data_source",
    F.concat_ws(". ", F.col("title"), F.coalesce(F.col("abstract"), F.lit(""))).alias("content")))
chunked = (text
    .select("*", F.posexplode(F.split("content", r"(?<=[.!?])\s+")).alias("chunk_index", "chunk"))
    .withColumn("chunk", F.trim("chunk"))
    .filter(F.length("chunk") > 0)
    .withColumn("chunk_id", F.concat_ws(":", "doi", F.col("chunk_index")))
    .withColumn("chunk_sha256", F.sha2("chunk", 256))
    .select("doi", "title", "chunk_id", "chunk", "document_sha256",
            "chunk_sha256", "citation_url", "data_source"))
chunked.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("silver_citation_chunks")

# COMMAND ----------
# Baseline retriever: per-term frequency weighted by inverse document frequency.
# This is a transparent lexical baseline, not a trained embedding or an LLM.
tokens = sorted(set(re.findall(r"[a-z0-9]+", query)))
if not tokens:
    raise ValueError("No searchable terms")
tf = (chunked.select("chunk_id", "doi", "title", "citation_url", "chunk",
                     F.explode(F.split(F.regexp_replace(F.lower("chunk"), "[^a-z0-9]+", " "),
                                       " ")).alias("term"))
    .filter(F.col("term").isin(tokens))
    .groupBy("chunk_id", "doi", "title", "citation_url", "chunk", "term")
    .agg(F.count("*").alias("term_frequency")))
n_chunks = chunked.count()
doc_frequencies = tf.groupBy("term").agg(F.countDistinct("chunk_id").alias("df"))
ranked = (tf.join(doc_frequencies, "term")
    .withColumn("idf", F.log((F.lit(n_chunks) + 1) / (F.col("df") + 1)))
    .withColumn("weighted_tf", F.col("term_frequency") * (F.col("idf") + F.lit(0.01)))
    .groupBy("doi", "chunk_id", "title", "citation_url", "chunk")
    .agg(F.sum("weighted_tf").alias("score"))
    .orderBy(F.col("score").desc(), F.col("chunk_id").asc())
    .limit(100))
ranked.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold_cited_retrieval_hits")

# COMMAND ----------
bronze_count = crossref.count() + europepmc.count()
valid_count = accepted.count()
rejected_count = rejected.count()
chunk_count = chunked.count()
assert valid_count + rejected_count == enriched.count()
assert selected.count() <= max_documents
assert chunked.groupBy("chunk_id").count().filter("count > 1").count() == 0
assert ranked.filter("citation_url NOT LIKE 'https://doi.org/%' OR citation_url IS NULL").count() == 0
assert ranked.filter("score < 0").count() == 0
assert ranked.join(accepted.select("doi"), "doi", "left_anti").count() == 0
print("PASS: two real scholarly data sources; source Bronze", bronze_count,
      "curated DOI works", valid_count, "rejected", rejected_count,
      "chunks", chunk_count, "retrieved citations", ranked.count())
display(spark.table("gold_cited_retrieval_hits").limit(20))

# COMMAND ----------
# MAGIC %md
# MAGIC ## What counts as evidence?
# MAGIC Record actual source page manifest SHA-256, DOI match counts, accepted
# MAGIC document counts and the top-K retrieved citation URLs.
# MAGIC Recall@K cannot be claimed without independent labelled relevance data.
# MAGIC This notebook intentionally does NOT bulk-download non-OA full text,
# MAGIC claim clinical correctness or use private patient information.
