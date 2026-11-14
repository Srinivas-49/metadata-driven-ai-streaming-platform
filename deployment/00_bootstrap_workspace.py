# Databricks notebook source
# MAGIC %md
# MAGIC # Synthetic AI documents and retrieval: schema and audit bootstrap
# MAGIC Does not create paid AI services, external model deployments or a new catalog.

# COMMAND ----------
import re
catalog = spark.sql("SELECT current_catalog() AS name").first()["name"]
if not re.fullmatch(r"[A-Za-z0-9_]+", catalog) or catalog == "hive_metastore":
    raise RuntimeError("Choose an existing writable Unity Catalog catalog")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`rag_portfolio` "
          "COMMENT 'Synthetic document ingestion and offline retrieval experiments'")
try:
    spark.sql(f"ALTER SCHEMA `{catalog}`.`rag_portfolio` SET TAGS "
              "('data_classification' = 'synthetic', 'project' = 'ai_retrieval')")
except Exception as exc:
    print("WARNING: catalog/schema exists but UC tags could not be applied:",
          type(exc).__name__, str(exc)[:240])
spark.sql("""
CREATE TABLE IF NOT EXISTS rag_portfolio.ops_quality_audit (
  checked_at TIMESTAMP,
  metric STRING,
  measured BIGINT,
  result STRING
) USING DELTA
""")
print("PASS: rag_portfolio writable schema and ops audit table")
