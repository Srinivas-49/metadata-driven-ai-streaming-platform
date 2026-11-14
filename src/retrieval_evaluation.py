"""Offline RAG evaluation of recall, reciprocal rank and access boundaries."""
from __future__ import annotations

def evaluate_cases(cases, retriever, top_k=3):
    """Retriever: callable(question, allowed_sources) -> ranked evidence dictionaries."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if not cases:
        raise ValueError("evaluation cases cannot be empty")
    pos, hit, reciprocal, negatives, false_hits, leaks = 0, 0, 0.0, 0, 0, 0
    for case in cases:
        allowed = set(case["allowed_sources"])
        results = retriever(case["question"], allowed)[:top_k]
        leaks += sum(result["source"] not in allowed for result in results)
        expected = case.get("expected_source")
        if expected:
            pos += 1
            rank = next((i for i, result in enumerate(results, 1)
                         if result["source"] == expected), None)
            hit += int(rank is not None)
            reciprocal += (1.0 / rank) if rank else 0.0
        else:
            negatives += 1
            false_hits += int(bool(results))
    return {
        "queries": len(cases),
        "positive_cases": pos,
        "negative_cases": negatives,
        "recall_at_k": round(hit / pos, 4) if pos else None,
        "mrr_at_k": round(reciprocal / pos, 4) if pos else None,
        "negative_false_positive_rate": round(false_hits / negatives, 4) if negatives else None,
        "unauthorized_evidence_count": leaks,
    }
