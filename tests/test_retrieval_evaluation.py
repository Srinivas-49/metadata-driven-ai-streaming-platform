import pytest
from src.retrieval_evaluation import evaluate_cases

def test_mean_reciprocal_rank_and_acls():
    cases = [
        {"question": "a", "allowed_sources": ["A"], "expected_source": "A"},
        {"question": "b", "allowed_sources": ["B"], "expected_source": "B"},
        {"question": "unknown", "allowed_sources": []},
    ]
    def search(q, allowed):
        return {"a": [{"source": "A"}], "b": [{"source": "X"}, {"source": "B"}],
                "unknown": [{"source": "X"}]}[q]
    metrics = evaluate_cases(cases, search)
    assert metrics["recall_at_k"] == 1
    assert metrics["mrr_at_k"] == 0.75
    assert metrics["unauthorized_evidence_count"] == 2
    assert metrics["negative_false_positive_rate"] == 1

def test_fail_on_empty_cases_or_topk():
    with pytest.raises(ValueError):
        evaluate_cases([], lambda *_: [])
    with pytest.raises(ValueError):
        evaluate_cases([{"question": "a", "allowed_sources": []}], lambda *_: [], top_k=0)
