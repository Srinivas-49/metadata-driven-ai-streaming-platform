# Metadata-Driven AI & Retrieval Platform

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
