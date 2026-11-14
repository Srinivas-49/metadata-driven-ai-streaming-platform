# Evaluation roadmap

Before presenting retrieval quality to recruiters, construct at least 30–50 independently labelled, non-duplicated questions across paraphrases, known answers, ambiguity and out-of-domain requests. Keep labels separate from index code, use frozen datasets, and record per-query matches, Recall@3, abstention accuracy and latency.

Do not label 100% on a three-question toy fixture as a production-level retrieval result. Apply paired before/after comparisons after adding Azure OpenAI, semantic embedding retrieval and hybrid BM25 + vector search.
