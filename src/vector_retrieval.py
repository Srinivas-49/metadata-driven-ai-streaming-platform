"""Embedding vector index with provider injection. Not an Azure AI Search deployment."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class IndexedChunk:
    id: str
    source: str
    text: str
    embedding: tuple[float, ...]

def normalize(vector):
    if not vector or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
        raise ValueError("Embedding must contain finite numbers")
    norm = math.sqrt(sum(float(v) ** 2 for v in vector))
    if norm <= 0:
        raise ValueError("Zero vector")
    return tuple(float(v) / norm for v in vector)

def build_index(chunks, embed_documents):
    if not chunks:
        raise ValueError("No documents")
    vectors = embed_documents([c["text"] for c in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Wrong vector count")
    index, dimension, used = [], None, set()
    for chunk, vector in zip(chunks, vectors):
        if chunk["id"] in used:
            raise ValueError("Duplicate source chunk ID")
        used.add(chunk["id"])
        emb = normalize(vector)
        if dimension is not None and len(emb) != dimension:
            raise ValueError("Inconsistent embedding dimensions")
        dimension = len(emb)
        index.append(IndexedChunk(chunk["id"], chunk["source"], chunk["text"], emb))
    return index

def search(question, index, embed_query, *, top_k=3, min_score=0.2):
    if not question.strip() or not index:
        return []
    if top_k < 1 or not -1 <= min_score <= 1:
        raise ValueError("Invalid retrieval configuration")
    query = normalize(embed_query(question))
    if len(query) != len(index[0].embedding):
        raise ValueError("Query embedding dimension mismatch")
    scored = []
    for item in index:
        score = sum(x * y for x, y in zip(query, item.embedding))
        if score >= min_score:
            scored.append({"id": item.id, "source": item.source, "text": item.text, "score": round(score, 6)})
    return sorted(scored, key=lambda x: (-x["score"], x["id"]))[:top_k]

def cited_answer(question, index, embed_query, *, min_score=0.2):
    matches = search(question, index, embed_query, min_score=min_score)
    if not matches:
        return {"answer": "Insufficient evidence in indexed documents.", "citations": [], "grounded": False}
    return {"answer": matches[0]["text"], "citations": [m["id"] for m in matches], "grounded": True}
