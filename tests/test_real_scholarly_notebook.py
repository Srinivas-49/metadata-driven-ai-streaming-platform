"""CI does not claim actual Databricks runtime or retrieval quality."""
import ast
from pathlib import Path

NOTEBOOK = Path("notebooks/03_real_scholarly_delta_retrieval.py")

def test_python_syntax():
    ast.parse(NOTEBOOK.read_text(encoding="utf-8"))

def test_two_sources_citations_and_quality():
    source = NOTEBOOK.read_text(encoding="utf-8")
    for key in ("crossref/page_*.jsonl", "europepmc/page_*.jsonl",
                "silver_doi_documents", "silver_citation_chunks",
                "gold_cited_retrieval_hits", "citation_url",
                "assert valid_count + rejected_count == enriched.count()"):
        assert key in source
