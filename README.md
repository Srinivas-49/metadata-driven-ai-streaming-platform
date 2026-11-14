# Metadata-Driven AI & Retrieval Platform

## Real scholarly metadata: OpenAlex + Crossref

A new real-source track ingests public works/DOI metadata from OpenAlex and Crossref, retaining source provenance and reconciling duplicate DOIs. It intentionally excludes publisher abstracts and PDFs (reuse rights may differ). This enables large-scale **bibliographic retrieval**, not yet full-text RAG.

```bash
export CROSSREF_CONTACT_EMAIL=YOUR_CONTACT_EMAIL
python -m scripts.fetch_research_catalogues --start 2025-01-01 --end 2025-01-31 --max-pages 1 --out raw-research
```

Upload the output folders into a Unity Catalog Volume and run `notebooks/03_real_scholarly_metadata_lakehouse.py` for Bronze ingestion, Silver record quality, DOI deduplication, lexical term indexing and Gold publication/term metrics.

[Source attribution and scale-aware ingest runbook](docs/REAL_SCHOLARLY_KNOWLEDGE_PLATFORM.md). **OpenAlex contains 300M+ works upstream; this repository does not claim to have ingested that many.**


## Real research-corpus pipeline (Crossref + Europe PMC)

The repository now has a **real-world scholarly ingestion track** using the public Crossref and Europe PMC REST APIs, DOI-based source reconciliation, cursor bookmarks, SHA-256 page manifests and a Databricks Spark Delta pipeline for citation-backed lexical retrieval.

- [Crossref + Europe PMC ingestion and licensing rules](real_data/README.md)
- [Real DOI enrichment, chunking and retrieval notebook](notebooks/03_real_scholarly_delta_retrieval.py)
- [Offline quality and checksum tests](tests/test_scholarly_real_sources.py)

This uses metadata and open-access-filtered research records only, not a bulk copyright-unclear full-text archive. The number of works indexed depends on actual API pages retrieved and source overlap; no millions-of-documents deployment is claimed.

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
