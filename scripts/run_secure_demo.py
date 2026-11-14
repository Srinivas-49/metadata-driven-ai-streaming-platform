"""Deterministic offline RAG demonstration with provenance and ACL filters."""
import hashlib
import json
import math
from src.secure_ingestion import ingest_manifest
from src.vector_retrieval import build_index
from src.retrieval_service import hybrid_search
from src.retrieval_evaluation import evaluate_cases
from src.metadata_rag import tokens

def embed(text):
    # Hashing vector is a deterministic local stand-in, NOT a trained embedding.
    vector = [0.0] * 256
    for word in tokens(text):
        bin_index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % len(vector)
        vector[bin_index] += 1
    return vector if any(vector) else [1.0] + [0.0] * 255

def main():
    corpus, provenance = ingest_manifest("data/config.json")
    index = build_index(corpus, lambda texts: [embed(text) for text in texts])
    def find(question, allowed):
        return hybrid_search(question, corpus, index, embed, allowed_sources=allowed)
    cases = [
        {"question": "Kafka consumer partitions", "allowed_sources": ["streaming"],
         "expected_source": "streaming"},
        {"question": "Delta Lake transactions", "allowed_sources": ["lakehouse"],
         "expected_source": "lakehouse"},
        {"question": "RAG retrieval embeddings", "allowed_sources": ["rag"],
         "expected_source": "rag"},
        {"question": "restricted", "allowed_sources": []},
    ]
    result = evaluate_cases(cases, find)
    assert result["unauthorized_evidence_count"] == 0
    assert result["recall_at_k"] is not None
    print(json.dumps({"provenance": provenance, "evaluation": result,
                      "sample_citations": [x["id"] for x in find("Kafka consumer partitions", {"streaming"})]},
                     indent=2))

if __name__ == "__main__":
    main()
