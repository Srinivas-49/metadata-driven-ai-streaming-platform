"""Bounded scholarly metadata ingestion from OpenAlex and Crossref.

This indexes work titles and bibliographic identifiers only: NO copyrighted
publisher abstracts, downloaded PDFs, account emails or private user data.
OpenAlex free key needed for cursor paging beyond page 1 as of Nov 2026.
All authentication via environment variables, never committed to Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works"
HOSTS = {"api.openalex.org", "api.crossref.org"}

def fetch_json(url, *, retries=3):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        raise ValueError("Only OpenAlex and Crossref HTTPS endpoints are permitted")
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers={"User-Agent":
                            "portfolio-scholarly-metadata/1.0 (open metadata only)"}), timeout=45) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
            delay = exc.headers.get("Retry-After", "") if exc.headers else ""
            time.sleep(min(10, int(delay)) if delay.isdigit() else 1 + attempt)
        except (URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(1 + attempt)

def clean_title(value):
    """Metadata titles only; no abstracts or attached publisher text."""
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()[:1000]

def normalize_doi(value):
    if not isinstance(value, str):
        return None
    doi = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi if doi.startswith("10.") and "/" in doi else None

def normalize_openalex(row):
    work_id = str(row.get("id") or "")
    title = clean_title(row.get("title"))
    doi = normalize_doi(row.get("doi"))
    return {
        "record_id": f"openalex:{work_id.rsplit('/', 1)[-1]}",
        "source": "OpenAlex", "doi": doi, "title": title,
        "year": row.get("publication_year"),
        "citation_count": row.get("cited_by_count"),
        "landing_url": work_id, "text_for_index": title,
        "copyright_scope": "metadata-title-only",
    }

def normalize_crossref(row):
    doi = normalize_doi(row.get("DOI"))
    parts = (row.get("published") or {}).get("date-parts") or []
    year = parts[0][0] if parts and parts[0] else None
    title = clean_title(row.get("title"))
    return {
        "record_id": f"crossref:{doi or 'missing'}",
        "source": "Crossref", "doi": doi, "title": title, "year": year,
        "citation_count": row.get("is-referenced-by-count"),
        "landing_url": f"https://doi.org/{doi}" if doi else None,
        "text_for_index": title, "copyright_scope": "metadata-title-only",
    }

def write_page(out_dir, source, index, records):
    directory = Path(out_dir) / source
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / f"works_p{index:04d}.jsonl"
    hash_value = hashlib.sha256()
    tmp = file.with_suffix(".partial")
    with tmp.open("wb") as destination:
        for record in records:
            line = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
            destination.write(line)
            hash_value.update(line)
    os.replace(tmp, file)
    return {"path": str(file), "records": len(records), "sha256": hash_value.hexdigest(),
            "bytes": file.stat().st_size}

def ingest(out_dir, *, sources=("openalex", "crossref"), start="2025-01-01",
           end="2025-01-31", page_size=50, max_pages=1, fetch=fetch_json):
    if not (date.fromisoformat(start) <= date.fromisoformat(end)):
        raise ValueError("Invalid publication date range")
    if not 1 <= page_size <= 100 or not 1 <= max_pages <= 100:
        raise ValueError("For safety use page_size<=100, max_pages<=100 per source")
    if not sources or set(sources) - {"openalex", "crossref"}:
        raise ValueError("Allowed sources: openalex and crossref")
    key = os.environ.get("OPENALEX_API_KEY", "")
    if "openalex" in sources and max_pages > 1 and not key:
        raise ValueError("OpenAlex cursor paging requires an API key; set OPENALEX_API_KEY locally")
    contact = os.environ.get("CROSSREF_CONTACT_EMAIL", "")
    if "crossref" in sources and "@" not in contact:
        raise ValueError("Supply CROSSREF_CONTACT_EMAIL for polite Crossref API access")
    outputs = []
    total = 0
    for source in sources:
        cursor = "*" if source == "crossref" or max_pages > 1 else None
        for page in range(max_pages):
            if source == "openalex":
                args = {
                    "filter": f"from_publication_date:{start},to_publication_date:{end}",
                    "per_page": page_size,
                    "select": "id,doi,title,publication_year,cited_by_count",
                }
                if cursor is not None:
                    args["cursor"] = cursor
                if key:
                    args["api_key"] = key
                url = OPENALEX + "?" + urlencode(args)
                payload = fetch(url)
                rows = payload.get("results", [])
                next_cursor = (payload.get("meta") or {}).get("next_cursor")
                normalize = normalize_openalex
            else:
                args = {
                    "filter": f"from-pub-date:{start},until-pub-date:{end}",
                    "rows": page_size, "cursor": cursor or "*",
                    "select": "DOI,title,published,is-referenced-by-count",
                    "mailto": contact,
                }
                url = CROSSREF + "?" + urlencode(args)
                payload = fetch(url)
                message = payload.get("message") or {}
                rows = message.get("items", [])
                next_cursor = message.get("next-cursor")
                normalize = normalize_crossref
            if not isinstance(rows, list):
                raise ValueError("Upstream works response must be a list")
            records = [normalize(row) for row in rows]
            if records:
                outputs.append(write_page(out_dir, source, page, records))
                total += len(records)
            if len(rows) < page_size or not next_cursor:
                break
            cursor = next_cursor
    manifest = {
        "sources": list(sources), "source_urls": [OPENALEX, CROSSREF],
        "publication_start": start, "publication_end_inclusive": end,
        "rows_written_before_cross_source_dedup": total,
        "max_records_possible": len(sources) * page_size * max_pages,
        "note": "Public bibliographic metadata only; no abstracts or article full texts",
        "files": outputs,
    }
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest_research.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="raw-research")
    parser.add_argument("--sources", nargs="+", default=["openalex", "crossref"])
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-01-31")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(ingest(args.out, sources=args.sources, start=args.start,
                            end=args.end, page_size=args.page_size,
                            max_pages=args.max_pages), indent=2))
