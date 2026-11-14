# Security, correctness and evaluation boundaries

## Implemented
- Source allowlist filtering **before** lexical and vector retrieval.
- Reciprocal-rank fusion across lexical and cosine similarity search.
- Extractive, source-cited answers and fail-closed abstention for no allowed sources.
- Deterministic unit tests covering access boundaries and labelled/negative queries.

## Essential limitations
- The caller **must** derive allowed_sources from a trusted identity/authorization layer. It must not trust a user-provided permission list.
- In-memory filtering is **not** a replacement for server-side database access control, encryption, tenant isolation or audit logging.
- RRF scores are relative ranks, not calibrated confidence probabilities.
- No live Azure Search index, production LLM, streaming Kafka service or regulatory certification is claimed.
- The evaluation set is only a toy fixture, not proof of real-world retrieval accuracy.

## Next production steps
Implement server-enforced tenant filters in a vector store; authentication and group sync; document expiry/deletion; prompt-injection testing; operational traces; embedding-version migrations; larger labelled evaluation fixtures.
