"""Metadata-configured ingestion and deterministic lexical retrieval baseline."""
import json
import math
import re
from collections import Counter
from pathlib import Path

def tokens(s):
    return re.findall(r"[a-z0-9]+", s.lower())

def chunks(text, max_words=50, overlap=10):
    if max_words <= 0 or not 0 <= overlap < max_words:
        raise ValueError("invalid chunk settings")
    words = text.split()
    stride = max_words - overlap
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), stride) if words[i:i + max_words]]

def ingest(config_path):
    config_path = Path(config_path)
    cfg = json.loads(config_path.read_text())
    for key in ("sources", "chunk_words", "overlap_words"):
        if key not in cfg:
            raise ValueError("missing config: " + key)
    corpus = []
    seen = set()
    for source in cfg["sources"]:
        path = config_path.parent / source["path"]
        for i, chunk in enumerate(chunks(path.read_text(encoding="utf-8"), cfg["chunk_words"], cfg["overlap_words"])):
            doc_id = f"{source['id']}:{i}"
            if doc_id in seen:
                raise ValueError("duplicate document id")
            seen.add(doc_id)
            corpus.append({
                "id": doc_id, "source": source["id"], "text": chunk, "tokens": tokens(chunk)
            })
    return corpus

def retrieve(question, corpus, k=3):
    query = set(tokens(question))
    n = len(corpus)
    if not query:
        return []
    df = Counter(t for doc in corpus for t in set(doc["tokens"]))
    scored = []
    for doc in corpus:
        tf = Counter(doc["tokens"])
        score = sum((1 + math.log(tf[t])) * math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in query if tf[t])
        if score > 0:
            scored.append((score, doc))
    return [
        {"score": round(score, 5), "id": doc["id"], "source": doc["source"], "text": doc["text"]}
        for score, doc in sorted(scored, key=lambda x: (-x[0], x[1]["id"]))[:k]
    ]

def answer(question, corpus):
    matches = retrieve(question, corpus)
    if not matches:
        return {"answer": "Insufficient evidence in indexed documents.", "citations": [], "grounded": False}
    return {
        "answer": matches[0]["text"],
        "citations": [x["id"] for x in matches],
        "grounded": True
    }

def evaluate(config_path, eval_path):
    corpus = ingest(config_path)
    questions = json.loads(Path(eval_path).read_text())
    hits = 0
    abstentions = 0
    for item in questions:
        matches = retrieve(item["question"], corpus, k=3)
        hits += int(any(m["source"] == item["expected_source"] for m in matches)) if item.get("expected_source") else 0
        abstentions += int(not matches)
    eligible = sum(bool(q.get("expected_source")) for q in questions)
    return {
        "questions": len(questions), "labelled_questions": eligible,
        "recall_at_3": round(hits / eligible, 4) if eligible else None,
        "abstentions": abstentions
    }
