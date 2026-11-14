"""Bounded, resumable scholarly metadata ingestion from TWO official APIs.

Crossref scholarly metadata and Europe PMC OPEN ACCESS research records.
No full text or proprietary content is downloaded or committed.
Never run large API crawls in GitHub CI; respect upstream quotas and licenses.
"""
from __future__ import annotations
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CROSSREF = "https://api.crossref.org/works"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
APPROVED = {"api.crossref.org", "www.ebi.ac.uk"}

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, value):
        self.parts.append(value)

def strip_markup(value):
    parser = TextOnly()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()

def doi_id(text):
    return str(text or "").strip().lower().removeprefix("https://doi.org/")

def get_json(url, *, retry=3, sleep=time.sleep):
    if urlparse(url).hostname not in APPROVED or urlparse(url).scheme != "https":
        raise ValueError("Unapproved scholarly API URL")
    for attempt in range(retry):
        try:
            req = Request(url, headers={"User-Agent": "ResearchPortfolio/1.0 (responsible public metadata ingestion)",
                                        "Accept": "application/json"})
            with urlopen(req, timeout=30) as response:
                if urlparse(response.geturl()).hostname not in APPROVED:
                    raise ValueError("Unexpected scholarly API redirect")
                return json.loads(response.read(16_000_000).decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt + 1 >= retry or (isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504)):
                raise
            sleep(min(2 ** attempt, 8))
    raise RuntimeError("unreachable")

def normalise_crossref(item):
    doi = doi_id(item.get("DOI"))
    titles = item.get("title") or []
    title = strip_markup(titles[0]) if isinstance(titles, list) and titles else ""
    if not doi or not title:
        return None
    return {"doi": doi, "title": title,
            "publisher": item.get("publisher") or "",
            "published": (item.get("published", {}).get("date-parts") or [[None]])[0][0],
            "citation_count": item.get("is-referenced-by-count", 0),
            "source": "crossref",
            "citation_url": "https://doi.org/" + doi}

def normalise_europepmc(item):
    # Europe PMC only; OPEN_ACCESS filter is checked again below.
    oa = str(item.get("isOpenAccess", "")).upper() in {"Y", "TRUE", "1"}
    doi = doi_id(item.get("doi"))
    if not oa or not doi or not item.get("title"):
        return None
    title = strip_markup(item.get("title", ""))
    abstract = strip_markup(item.get("abstractText", ""))[:10000]
    if not title:
        return None
    return {"doi": doi, "title": title, "abstract": abstract,
            "pub_year": item.get("pubYear"),
            "source": "europepmc_open_access",
            "citation_url": "https://doi.org/" + doi}

def write_pages(root, source, *, topic="data engineering", pages=2, page_size=25, start_page=0, fetch=get_json, pause=0):
    if source not in ("crossref", "europepmc"):
        raise ValueError("Unknown provider")
    if not 1 <= page_size <= 1000 or not 1 <= pages <= 1000 or not 0 <= start_page <= 100000:
        raise ValueError("page_size 1..1000, pages 1..1000 and start_page 0..100000")
    if not 1 <= len(topic) <= 100 or any(ord(c) < 32 for c in topic):
        raise ValueError("Invalid topic")
    folder = Path(root) / source
    folder.mkdir(parents=True, exist_ok=True)
    old_manifest_path = folder / "manifest.json"
    previous = json.loads(old_manifest_path.read_text()) if old_manifest_path.exists() else None
    if previous and (previous["source"] != source or previous["topic"] != topic
                     or previous["page_size"] != page_size):
        raise ValueError("Source parameters changed; use a separate landing folder")
    previous_entries = {item["filename"]: item for item in (previous or {}).get("pages", [])}
    cursor = "*"
    if start_page:
        prev_path = folder / f"page_{start_page - 1:06d}.jsonl"
        prev_bookmark = folder / f"page_{start_page - 1:06d}.cursor.json"
        tracked = previous_entries.get(prev_path.name)
        if not tracked or not prev_path.is_file() or not prev_bookmark.is_file():
            raise ValueError("Cannot resume from an unverified previous page")
        if hashlib.sha256(prev_path.read_bytes()).hexdigest() != tracked["sha256"]:
            raise ValueError("Previous scholarly page checksum mismatch")
        cursor = json.loads(prev_bookmark.read_text())["next_cursor"]
        if not cursor:
            raise ValueError("Missing page cursor for resumed crawl")
    entries = dict(previous_entries)
    for index in range(start_page, start_page + pages):
        path = folder / f"page_{index:06d}.jsonl"
        bookmark = folder / f"page_{index:06d}.cursor.json"
        if path.is_file() and bookmark.is_file():
            data = path.read_bytes()
            count = len(data.splitlines())
            sha = hashlib.sha256(data).hexdigest()
            previous_entry = previous_entries.get(path.name)
            if not previous_entry or previous_entry["sha256"] != sha:
                raise ValueError("Cached scholarly page is untracked or corrupt")
            cursor = json.loads(bookmark.read_text())["next_cursor"]
        elif path.exists() or bookmark.exists():
            raise ValueError("Partial source download, restore both page and cursor or restart")
        else:
            if source == "crossref":
                url = CROSSREF + "?" + urlencode({
                    "query.bibliographic": topic, "rows": page_size,
                    "cursor": cursor, "select": "DOI,title,publisher,published,is-referenced-by-count"})
                data = fetch(url)
                items = data["message"]["items"]
                next_cursor = data["message"].get("next-cursor") or cursor
                parsed = [normalise_crossref(item) for item in items]
            else:
                # OPEN_ACCESS ensures this does not bulk-ingest restricted content.
                url = EUROPE_PMC + "?" + urlencode({
                    "query": f"({topic}) AND OPEN_ACCESS:Y",
                    "resultType": "core", "format": "json", "pageSize": page_size,
                    "cursorMark": cursor})
                data = fetch(url)
                items = data["resultList"]["result"]
                next_cursor = data.get("nextCursorMark") or cursor
                parsed = [normalise_europepmc(item) for item in items]
            records = [record for record in parsed if record]
            contents = b"".join((json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n").encode()
                                for item in records)
            path.write_bytes(contents)
            bookmark.write_text(json.dumps({"next_cursor": next_cursor}))
            cursor = next_cursor
            count = len(records)
            sha = hashlib.sha256(contents).hexdigest()
            if pause:
                time.sleep(pause)
        entries[path.name] = {"filename": path.name, "records": count, "sha256": sha}
        if count < page_size:
            # Pages can be partially filtered by null DOI/OA validation; don't
            # interpret source exhaustion from normalized rows alone.
            # In scale runs, continue page count but stop when cursor stops.
            if cursor == "*":
                break
    pages_index = [entries[key] for key in sorted(entries)]
    manifest = {"source": source, "topic": topic, "page_size": page_size,
                "pages": pages_index, "normalized_records": sum(x["records"] for x in pages_index),
                "last_cursor": cursor}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest

def read_normalized(root, source):
    folder = Path(root) / source
    manifest = json.loads((folder / "manifest.json").read_text())
    for entry in manifest["pages"]:
        data = (folder / entry["filename"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Checksum mismatch")
        for line in data.splitlines():
            yield json.loads(line)

def build_index_manifest(root):
    """DOI dedup and Crossref+Europe PMC enrichment; no hallucinated join rate."""
    crossref = {row["doi"]: row for row in read_normalized(root, "crossref")}
    epmc = {row["doi"]: row for row in read_normalized(root, "europepmc")}
    joined = []
    for doi in sorted(set(crossref) | set(epmc)):
        left, right = crossref.get(doi, {}), epmc.get(doi, {})
        joined.append({"doi": doi, "title": right.get("title") or left.get("title"),
                       "publisher": left.get("publisher", ""),
                       "abstract": right.get("abstract", ""),
                       "citation_url": "https://doi.org/" + doi,
                       "sources": [name for name, match in (("crossref", left), ("europepmc", right)) if match]})
    output = Path(root) / "enriched_research.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for doc in joined:
            handle.write(json.dumps(doc, sort_keys=True) + "\n")
    metrics = {"crossref_dois": len(crossref), "europepmc_oa_dois": len(epmc),
               "matched_dois": len(set(crossref) & set(epmc)),
               "unique_dois": len(joined), "output": str(output)}
    (Path(root) / "quality_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="real-data/scholarly")
    p.add_argument("--topic", default="data engineering")
    p.add_argument("--pages", type=int, default=2)
    p.add_argument("--start-page", type=int, default=0)
    p.add_argument("--page-size", type=int, default=25)
    p.add_argument("--confirm-large", action="store_true")
    a = p.parse_args()
    if (a.pages > 10 or a.start_page > 0) and not a.confirm_large:
        p.error("Large or resumed external crawls require --confirm-large and quota review")
    for provider in ("crossref", "europepmc"):
        print(json.dumps(write_pages(a.out, provider, topic=a.topic,
                                     pages=a.pages, page_size=a.page_size,
                                     start_page=a.start_page), indent=2))
    print(json.dumps(build_index_manifest(a.out), indent=2))

if __name__ == "__main__":
    main()
