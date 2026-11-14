import pytest
from src.vector_retrieval import build_index, cited_answer, normalize, search

CORPUS = [
    {"id": "lakehouse:0", "source": "lakehouse", "text": "Bronze Silver Gold medallion layers"},
    {"id": "stream:0", "source": "stream", "text": "Kafka event partitions"},
    {"id": "ai:0", "source": "ai", "text": "RAG retrieval embeddings"},
]
VECTORS = {CORPUS[0]["text"]: [1, 0, 0], CORPUS[1]["text"]: [0, 1, 0], CORPUS[2]["text"]: [0, 0, 1]}

def embed_documents(texts):
    return [VECTORS[t] for t in texts]

def embed_query(q):
    return {"lakehouse": [1, 0, 0], "stream": [0, 1, 0], "rag": [0, 0, 1], "unknown": [-1, -1, -1]}[q]

def test_vectors_and_citations():
    index = build_index(CORPUS, embed_documents)
    assert search("lakehouse", index, embed_query)[0]["id"] == "lakehouse:0"
    assert cited_answer("rag", index, embed_query)["citations"][0] == "ai:0"

def test_abstains_without_retrieval_evidence():
    result = cited_answer("unknown", build_index(CORPUS, embed_documents), embed_query)
    assert result["grounded"] is False and result["citations"] == []

def test_invalid_vectors():
    with pytest.raises(ValueError): normalize([0, 0])
    with pytest.raises(ValueError): normalize([float("nan"), 0])
    with pytest.raises(ValueError): build_index(CORPUS, lambda _: [[1, 0]] * 2)

def test_embedding_dimension_contract():
    index = build_index(CORPUS, embed_documents)
    with pytest.raises(ValueError): search("lakehouse", index, lambda _: [1, 0])
    with pytest.raises(ValueError): build_index(CORPUS, lambda _: [[1, 0], [0, 1, 0], [1, 0]])
