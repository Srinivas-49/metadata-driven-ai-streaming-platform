from dataclasses import dataclass
import pytest
from src.retrieval_service import hybrid_search, cited_answer, evaluate_recall_at_k

@dataclass(frozen=True)
class Vector:
    id: str
    source: str
    text: str
    embedding: tuple

CORPUS = [
    {"id": "pub:0", "source": "pub", "text": "Delta Lake transaction", "tokens": ["delta", "lake", "transaction"]},
    {"id": "restricted:0", "source": "restricted", "text": "private audit record", "tokens": ["private", "audit", "record"]},
]
VECTORS = [Vector("pub:0", "pub", "Delta Lake transaction", (1, 0)), Vector("restricted:0", "restricted", "private audit record", (0, 1))]

def embedding(query):
    return [1, 0] if "delta" in query.lower() else [0, 1]

def test_scoped_hybrid_and_citations():
    result = cited_answer("Delta Lake", CORPUS, VECTORS, embedding, allowed_sources={"pub"})
    assert result["grounded"] and result["citations"] == ["pub:0"]

def test_denied_source_does_not_leak():
    hits = hybrid_search("private audit record", CORPUS, VECTORS, embedding, allowed_sources={"pub"})
    assert all(h["source"] == "pub" for h in hits)

def test_fail_closed_no_embeddings_called():
    def forbidden(_):
        raise AssertionError("embedding must not be called without access")
    assert not cited_answer("private", CORPUS, VECTORS, forbidden, allowed_sources=set())["grounded"]

def test_invalid_config():
    with pytest.raises(ValueError):
        hybrid_search("delta", CORPUS, VECTORS, embedding, allowed_sources={"pub"}, top_k=0)

def test_labelled_evaluation():
    cases = [{"question": "delta", "expected_source": "pub"}, {"question": "unknown"}]
    def lookup(q):
        return [{"source": "pub"}] if q == "delta" else []
    result = evaluate_recall_at_k(cases, lookup)
    assert result["recall_at_k"] == 1.0 and result["negative_false_positive_rate"] == 0.0
