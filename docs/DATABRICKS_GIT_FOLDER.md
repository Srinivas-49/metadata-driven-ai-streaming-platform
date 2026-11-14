# Databricks Free Edition Git folder for the AI retrieval project

**This is a setup guide, not confirmation that workspace folders have been created.**

Git folder: metadata-driven-ai-retrieval
Repository URL: https://github.com/Srinivas-49/metadata-driven-ai-streaming-platform.git
Branch: main

Within your Databricks workspace, choose Workspace -> home -> Create -> Git folder. Clone the public repository using your own GitHub integration. Run:
1. notebooks/01_spark_document_ingestion.py — Spark synthetic documents, sentence chunks, document hashes, managed Delta Bronze/Silver tables.
2. notebooks/02_spark_retrieval_evaluation.py — source ACL filtering before lexical retrieval, citations, abstention tests, relevance evaluation and Gold metrics.

These notebooks need no Azure AI Search instance or external model keys. The repository also contains independent local hybrid vector retrieval code under src; the Spark notebooks specifically demonstrate a lexical evaluation baseline. Real production retrieval needs server-side permission filters, authentication, versioned embeddings and much larger evaluated corpora.
