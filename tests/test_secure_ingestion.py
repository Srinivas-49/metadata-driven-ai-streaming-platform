import json
import pytest
from src.secure_ingestion import ingest_manifest

def config(tmp_path, sources, max_words=5, overlap=1):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"sources": sources, "chunk_words": max_words, "overlap_words": overlap}))
    return p

def test_provenance_and_chunk_citations(tmp_path):
    (tmp_path / "first.txt").write_text("one two three four five six")
    corpus, origin = ingest_manifest(config(tmp_path, [{"id": "first", "path": "first.txt"}]))
    assert [c["id"] for c in corpus] == ["first:0", "first:1"]
    assert len(origin[0]["sha256"]) == 64
    assert all(c["sha256"] == origin[0]["sha256"] for c in corpus)

def test_rejects_escape_and_duplicate_ids(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "_outside.txt")
    outside.write_text("private")
    with pytest.raises(ValueError, match="outside allowed"):
        ingest_manifest(config(tmp_path, [{"id": "outside", "path": "../" + outside.name}]))
    (tmp_path / "first.txt").write_text("safe")
    with pytest.raises(ValueError, match="duplicate"):
        ingest_manifest(config(tmp_path, [
            {"id": "repeat", "path": "first.txt"}, {"id": "repeat", "path": "first.txt"}]))

def test_rejects_file_extension_large_file_and_bad_chunk_settings(tmp_path):
    (tmp_path / "secret.json").write_text("{}")
    with pytest.raises(ValueError, match="unsupported"):
        ingest_manifest(config(tmp_path, [{"id": "secrets", "path": "secret.json"}]))
    (tmp_path / "huge.txt").write_text("x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="size limit"):
        ingest_manifest(config(tmp_path, [{"id": "huge", "path": "huge.txt"}]))
    with pytest.raises(ValueError, match="chunk"):
        ingest_manifest(config(tmp_path, [{"id": "huge", "path": "huge.txt"}], max_words=0))
