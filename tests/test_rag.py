from src.metadata_rag import chunks, ingest, retrieve, answer, evaluate

def test_chunk_overlap():
    assert chunks("a b c d e f", 4, 2) == ["a b c d", "c d e f", "e f"]

def test_retrieval():
    corpus = ingest("data/config.json")
    assert retrieve("Kafka consumer partitions", corpus)[0]["source"] == "streaming"
    assert answer("Delta Lake transactions", corpus)["citations"]

def test_abstention():
    assert answer("zzzxxyyq", ingest("data/config.json"))["grounded"] is False

def test_eval():
    metrics = evaluate("data/config.json", "data/evaluation.json")
    assert metrics["questions"] == 3
    assert 0 <= metrics["recall_at_3"] <= 1
