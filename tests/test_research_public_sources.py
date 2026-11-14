import json
from urllib.parse import parse_qs, urlparse
import pytest
from scripts.fetch_research_catalogues import (
    ingest, normalize_openalex, normalize_crossref, fetch_json)

def test_identifier_and_rights_safe_metadata():
    first = normalize_openalex({
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.5555/ABC",
        "title": "Public <b>Graph</b> Study", "publication_year": 2025,
        "abstract_inverted_index": {"secret": [1]}})
    second = normalize_crossref({"DOI": "10.5555/abc",
                                 "title": ["Public Graph Study"],
                                 "published": {"date-parts": [[2025, 1, 9]]},
                                 "abstract": "Do not store publisher copyrighted text"})
    assert first["doi"] == second["doi"]
    assert first["title"] == "Public Graph Study"
    assert second["year"] == 2025
    assert all("abstract" not in item for item in (first, second))

def test_paged_ingestion_and_hash_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "dummy-unit-test-only")
    monkeypatch.setenv("CROSSREF_CONTACT_EMAIL", "test@example.org")
    calls = []
    def fake(url):
        calls.append(url)
        if "openalex" in url:
            return {"results": [
                {"id": "https://openalex.org/W1", "doi": "10.1/one", "title": "Graphs"},
                {"id": "https://openalex.org/W2", "doi": "10.2/two", "title": "Systems"}],
                "meta": {"next_cursor": "NEXT"}} if "cursor=%2A" in url else {"results": [], "meta": {}}
        return {"message": {"items": [{"DOI": "10.1/one", "title": ["Graphs"]}],
                            "next-cursor": "NEXT"}}
    result = ingest(tmp_path, max_pages=2, page_size=2, fetch=fake)
    assert result["rows_written_before_cross_source_dedup"] == 3
    assert len(result["files"]) == 2
    assert all(len(item["sha256"]) == 64 for item in result["files"])
    assert "dummy-unit-test-only" not in (tmp_path / "manifest_research.json").read_text()
    assert "test@example.org" not in (tmp_path / "manifest_research.json").read_text()
    assert json.loads(next((tmp_path / "openalex").glob("*.jsonl")).read_text().splitlines()[0])["source"] == "OpenAlex"

def test_api_budget_and_host_guard(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    with pytest.raises(ValueError, match="requires an API key"):
        ingest(tmp_path, sources=("openalex",), max_pages=2, fetch=lambda url: {})
    with pytest.raises(ValueError):
        fetch_json("https://example.net/works")
    with pytest.raises(ValueError):
        ingest(tmp_path, sources=("other",), fetch=lambda url: {})
