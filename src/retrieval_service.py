"""Permission-scoped hybrid retrieval; calling service must supply trusted allowlist."""
from collections.abc import Collection
from src.metadata_rag import retrieve
from src.vector_retrieval import search

def hybrid_search(question, corpus, vectors, embed_query, *, allowed_sources: Collection[str], top_k=3, min_vector_score=0.2):
    """Filter before retrieval; combine lexical and dense ranks with RRF."""
    if top_k < 1:
        raise ValueError("top_k must be >=1")
    allowed = set(allowed_sources)
    if not allowed or not question.strip():
        return []
    filtered = [doc for doc in corpus if doc["source"] in allowed]
    filtered_vectors = [doc for doc in vectors if doc.source in allowed]
    lexical = retrieve(question, filtered, k=max(top_k, 20)) if filtered else []
    dense = search(question, filtered_vectors, embed_query, top_k=max(top_k, 20), min_score=min_vector_score) if filtered_vectors else []
    documents, scores = {}, {}
    for hits in (lexical, dense):
        for rank, hit in enumerate(hits, 1):
            documents.setdefault(hit["id"], {"id": hit["id"], "source": hit["source"], "text": hit["text"]})
            scores[hit["id"]] = scores.get(hit["id"], 0) + 1 / (60 + rank)
    return [{**documents[key], "rrf_score": round(score, 8)}
            for key, score in sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]]

def cited_answer(question, corpus, vectors, embed_query, *, allowed_sources, top_k=3):
    hits = hybrid_search(question, corpus, vectors, embed_query, allowed_sources=allowed_sources, top_k=top_k)
    if not hits:
        return {"answer": "Insufficient authorised evidence in indexed documents.", "citations": [], "grounded": False}
    return {"answer": hits[0]["text"], "citations": [h["id"] for h in hits], "grounded": True}

def evaluate_recall_at_k(cases, retriever, *, k=3):
    """Treat negative examples separately; report both retrieval and false positives."""
    if k < 1:
        raise ValueError("k must be positive")
    positives = [c for c in cases if c.get("expected_source")]
    negatives = [c for c in cases if not c.get("expected_source")]
    hits = sum(any(h["source"] == c["expected_source"] for h in retriever(c["question"])[:k]) for c in positives)
    false_hits = sum(bool(retriever(c["question"])[:k]) for c in negatives)
    return {"labelled_cases": len(positives), "negative_cases": len(negatives),
            "recall_at_k": round(hits / len(positives), 4) if positives else None,
            "negative_false_positive_rate": round(false_hits / len(negatives), 4) if negatives else None}
