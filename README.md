# Metadata-Driven AI & Streaming Data Platform

**Status:** Locally tested, metadata-configured document ingestion and **offline lexical retrieval baseline**. Optional Azure OpenAI + LangChain components are integration examples, not production deployments. **There is no deployed vector database, live LLM service, or streaming pipeline in this repository.**

## Problem / solution
Maintaining source-specific ingestion code is difficult, and ungrounded generated answers are hard to audit. Configuration JSON identifies approved documents and chunk settings. A deterministic lexical index supports source-cited, extractive answers and abstention when evidence is missing.

**Architecture:** JSON metadata -> document ingestion -> overlapping chunks -> lexical retrieval -> extractive response + citations -> labelled evaluation.

## Quickstart
```bash
python -m scripts.run_demo
python -m pytest -q
```

## AI integration path
`integrations/azure_openai_langchain_example.py` shows how to initialise Azure OpenAI chat and embeddings clients with LangChain, with credentials supplied by environment variables. Install `langchain-openai` to use that module. It is not called by the local demo or CI.

A production RAG implementation needs Azure AI Search vector/hybrid indexing, document-level ACL filtering, embedding version control, idempotent reindexing, retrieval/faithfulness evaluation, prompt injection defenses, observability, error budgets and cost controls. Kafka streaming ingestion is an architectural extension only, not implemented.

## Evaluation limitations
A three-question synthetic fixture evaluates Recall@3. Results are a toy demonstration, not a measured production retrieval-accuracy claim. `grounded=True` means an extractive answer was returned from a document, not that the document itself is factually correct.

## Interview topics
Schema-driven ingestion, chunk overlap, sparse vs dense retrieval, RAG evaluation, precision/recall, tenant isolation, prompt injection, access control, vector indexing, model drift, feedback loops and token budgets.