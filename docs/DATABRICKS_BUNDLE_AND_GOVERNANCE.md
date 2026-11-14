# AI retrieval platform: catalog, tags, notebooks and paused job

This repo contains synthetic document-retrieval exercises. It is NOT a connected production RAG service, and no Azure OpenAI, Azure AI Search or LLM endpoint is provisioned by this bundle.

## Setup in your own Databricks workspace
1. Open the *actual* Databricks workspace URL, not an Azure Logic Apps signed HTTP trigger. Rotate the previously shared Logic Apps key.
2. Workspace > Create > Git folder, clone https://github.com/Srinivas-49/metadata-driven-ai-streaming-platform.git from main.
3. Run deployment/00_bootstrap_workspace.py to prepare rag_portfolio and audit tables in the current Unity Catalog catalog. Review any tag permission warnings.
4. Run notebooks/01_spark_document_ingestion.py for synthetic documents and SHA-256 source hashes.
5. Run notebooks/02_spark_retrieval_evaluation.py for ACL-scoped lexical retrieval, citations, negative queries and Gold evaluation metrics.
6. Run deployment/90_validate_retrieval.py for final table, uniqueness, ACL leak and evaluation gate.
7. If privileges permit, run governance/POST_RUN_TAGS.sql to classify Bronze/Silver/Gold tables.

## Jobs-as-code, disabled schedule
The root databricks.yml defines a four-task dependency graph, maximum one simultaneous run, serverless notebook tasks, and a daily schedule set to PAUSED.

On your own authenticated machine, after reviewing workspace and credit balance:

    databricks auth login --host https://YOUR-REAL-DATABRICKS-WORKSPACE
    databricks bundle validate -t dev
    databricks bundle deploy -t dev
    databricks bundle run synthetic_retrieval_evaluation -t dev

If the Free Edition account blocks bundle deployment, use the four notebooks manually. A paid Azure Databricks workspace may incur compute charges whenever a job is run even with the schedule paused.

## What is not done
- No live workspace login, catalog/schema, file, folder or job creation.
- No actual Databricks test run.
- No identity provider or server-side data access policy; the tests demonstrate local allowlisting only.
- No production retrieval accuracy or regulatory compliance claims.

Extend with external identity integration, server-side ACL filtering, versioned embeddings and evaluation on a large labelled dataset only after privacy and cost approvals.
