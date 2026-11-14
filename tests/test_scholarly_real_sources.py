"""Offline mock API test: no huge Crossref/Europe PMC crawl in GitHub Actions."""
import json
from urllib.parse import parse_qs, urlparse
import pytest
from real_data.scholarly_sources import (
    write_pages, read_normalized, build_index_manifest, strip_markup,
    normalise_crossref, normalise_europepmc
)

def test_metadata_and_open_access_join(tmp_path):
    def fake_fetch(url):
        q = parse_qs(urlparse(url).query)
        if "crossref" in url:
            assert q["rows"] == ["2"]
            return {"message": {"items": [
                {"DOI": "10.1000/abc", "title": ["<i>Delta</i> Paper"],
                 "publisher": "Publisher", "published": {"date-parts": [[2025]]}},
                {"DOI": "10.1000/def", "title": ["Other Study"],
                 "publisher": "Publisher", "published": {"date-parts": [[2025]]}}],
                "next-cursor": "next"}}
        assert "OPEN_ACCESS:Y" in q["query"][0]
        return {"resultList": {"result": [
            {"doi": "10.1000/ABC", "title": "Delta Paper", "abstractText": "<p>Evidence.</p>",
             "isOpenAccess": "Y", "pubYear": "2025"},
            {"doi": "10.1000/private", "title": "Secret", "abstractText": "Not accessible",
             "isOpenAccess": "N", "pubYear": "2025"}]},
            "nextCursorMark": "next"}
    for provider in ("crossref", "europepmc"):
        write_pages(tmp_path, provider, topic="data science", pages=1,
                    page_size=2, fetch=fake_fetch)
    metrics = build_index_manifest(tmp_path)
    assert metrics["matched_dois"] == 1
    assert metrics["unique_dois"] == 2
    assert metrics["europepmc_oa_dois"] == 1
    records = (tmp_path / "enriched_research.jsonl").read_text().splitlines()
    assert "Evidence." in records[0]
    assert "private" not in str(records)

def test_markup_normalization_and_reject_non_oa():
    assert strip_markup("<p>Some <b>bold</b> abstract</p>") == "Some bold abstract"
    assert normalise_europepmc({"doi": "10.abc/test", "title": "Title",
                                  "isOpenAccess": "N"}) is None
    assert normalise_crossref({"DOI": "", "title": ["bad"]}) is None

def test_checksum_and_page_limits(tmp_path):
    write_pages(tmp_path, "crossref", pages=1, fetch=lambda u: {
        "message": {"items": [{"DOI": "10.1000/valid", "title": ["Valid"]}],
                    "next-cursor": "next"}})
    assert len(list(read_normalized(tmp_path, "crossref"))) == 1
    (tmp_path / "crossref" / "page_000000.jsonl").write_text("corrupt")
    with pytest.raises(ValueError, match="Checksum"):
        list(read_normalized(tmp_path, "crossref"))
    with pytest.raises(ValueError):
        write_pages(tmp_path, "crossref", pages=1001)

def test_cursor_resumes_beyond_first_batch(tmp_path):
    calls = []
    def fake_fetch(url):
        cursor = parse_qs(urlparse(url).query)["cursor"][0]
        calls.append(cursor)
        assert cursor in ("*", "NEXT")
        return {"message": {"items": [
            {"DOI": "10.1000/first" if cursor == "*" else "10.1000/second",
             "title": ["First" if cursor == "*" else "Second"]}],
            "next-cursor": "NEXT" if cursor == "*" else "END"}}
    a = write_pages(tmp_path, "crossref", topic="testing", page_size=1,
                    pages=1, start_page=0, fetch=fake_fetch)
    b = write_pages(tmp_path, "crossref", topic="testing", page_size=1,
                    pages=1, start_page=1, fetch=fake_fetch)
    assert a["normalized_records"] == 1 and b["normalized_records"] == 2
    assert calls == ["*", "NEXT"]
    assert [r["doi"] for r in read_normalized(tmp_path, "crossref")] == [
        "10.1000/first", "10.1000/second"]
    with pytest.raises(ValueError, match="parameters changed"):
        write_pages(tmp_path, "crossref", topic="other", page_size=1,
                    pages=1, start_page=1, fetch=fake_fetch)
