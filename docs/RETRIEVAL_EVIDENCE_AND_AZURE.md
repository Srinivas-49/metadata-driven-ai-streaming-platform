# Offline RAG security, evaluation and Azure integration blueprint

This repo now has secure_ingestion.py for bounded manifests, source IDs and SHA-256 lineage. It validates that sources resolve within the configured directory, rejects unsupported extensions and duplicate IDs, and limits local file size. This is not an antivirus scanner or an authorization system.

Use:
    python -m pytest -q
    python -m scripts.run_secure_demo

Demo: local deterministic hashing vectors, cosine search, lexical retrieval, permission-scoped fusion, source-cited evidence, Recall@3, mean reciprocal rank, negative false positive rate and unauthorized evidence checks. Hash-based vectors are NOT a pretrained embedding model and scores are not calibrated confidence. The demonstration keeps no real personal data.

Azure plan: reuse the enterprise repo's Key Vault and storage. infra/azure/search_free.bicep declares an OPTIONAL Azure AI Search Free service, subject to account quota and regional availability. Preview first; nothing here automatically provisions it. Azure OpenAI is optional and may have separate token and deployment costs; no model deployment or real-world faithfulness benchmark is claimed.

Production needs server-enforced document ACL filtering, authenticated identities, chunk/document deletion, versioned embeddings, audit logs, threat modeling, injection resistance, external red-team tests, and governance controls before any sensitive documents are used. Do not upload NHS/health or customer data to an unapproved personal/free service.
