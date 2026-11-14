# Metadata-Driven AI & Retrieval Platform

> **2026 portfolio upgrade:** Bounded source ingestion with SHA-256 provenance, deterministic offline retrieval evaluation, access-scope leakage checks and reproducible artifacts. No model credentials or paid cloud resources are needed for the demo.

### Offline retrieval-validation evidence

    python -m pytest -q
    python -m scripts.run_secure_demo

The sample uses local hash-based vectors (not pretrained embeddings), lexical/vector fusion, source allowlists, citations, recall, reciprocal rank and negative-query evaluation. GitHub CI publishes the evaluation JSON as an artifact. Results are **toy fixture measurements**, not production LLM quality or regulatory compliance.

- [Security and evaluation runbook](docs/RETRIEVAL_EVIDENCE_AND_AZURE.md)
- [Optional, manual-only Azure AI Search Free resource](infra/azure/search_free.bicep)
- [Permission-scoped hybrid retrieval](src/retrieval_service.py)



**Status:** local, testable proof of concept. Metadata-configured ingestion, lexical retrieval, embedding-vector search, hybrid ranking, extractive citations and abstention. Optional Azure OpenAI/LangChain adapters are examples, not evidence of deployment.

## Architecture
JSON document manifest → overlapping chunks → lexical and injected vector retrieval → **trusted source allowlist** → reciprocal-rank fusion → source-cited extractive answer or abstention.

## Run
```bash
python -m pip install pytest
python -m pytest -q
python -m scripts.run_demo
```

- `src/metadata_rag.py`: local ingestion, lexical retrieval and sample evaluation.
- `src/vector_retrieval.py`: provider-independent embedding search using cosine similarity.
- `src/retrieval_service.py`: permission-scoped hybrid search, answer and evaluation helpers.
- `docs/SECURITY_AND_EVALUATION.md`: security boundaries and production roadmap.

**Important:** `allowed_sources` must be supplied by a **trusted** service. The code does not authenticate users, enforce vector-database permissions, or deploy an Azure resource. RRF ranks are not confidence probabilities and sample tests do not establish clinical or production reliability.
