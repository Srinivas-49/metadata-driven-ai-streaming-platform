"""Auditable, bounded local document ingestion for a zero-cost retrieval demo.

Not an identity provider or a malware scanner. Never use this in place of a
server-side tenant authorization layer when handling real private documents.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from src.metadata_rag import chunks, tokens

ALLOWED_SUFFIXES = {".txt", ".md"}
MAX_FILE_BYTES = 1024 * 1024

def ingest_manifest(config_path):
    path = Path(config_path)
    root = path.parent.resolve()
    conf = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(conf, dict) or not isinstance(conf.get("sources"), list):
        raise ValueError("sources must be a list")
    max_words, overlap = conf.get("chunk_words"), conf.get("overlap_words")
    if (type(max_words) is not int or type(overlap) is not int
            or not 1 <= max_words <= 2048 or not 0 <= overlap < max_words):
        raise ValueError("invalid chunk settings")
    if not conf["sources"]:
        raise ValueError("no sources")
    seen, corpus, provenance = set(), [], []
    for entry in conf["sources"]:
        if not isinstance(entry, dict):
            raise ValueError("malformed source")
        source_id, rel = entry.get("id"), entry.get("path")
        if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", source_id):
            raise ValueError("invalid source id")
        if source_id in seen:
            raise ValueError("duplicate source id")
        seen.add(source_id)
        if not isinstance(rel, str) or not rel:
            raise ValueError("invalid source path")
        source = (root / rel).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError("path outside allowed source directory or not a file")
        if source.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("unsupported document type")
        if source.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("document exceeds size limit")
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        provenance.append({"source": source_id, "path": str(source.relative_to(root)),
                           "sha256": digest, "bytes": len(raw)})
        for index, content in enumerate(chunks(text, max_words=max_words, overlap=overlap)):
            corpus.append({"id": f"{source_id}:{index}", "source": source_id,
                           "text": content, "tokens": tokens(content),
                           "sha256": digest})
    return corpus, provenance
