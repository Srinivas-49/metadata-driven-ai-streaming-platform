# Real-world research data: OpenAlex + Crossref

Sources:
- OpenAlex works API: https://api.openalex.org/works
- Crossref REST works API: https://api.crossref.org/works

OpenAlex indexes more than 300 million scholarly works, but this project **does not** claim to have downloaded that many. Crossref provides DOI and publisher-deposited metadata. Publisher abstracts and paper full text can have copyright restrictions, therefore the safe default ingestion **excludes both**. Only public bibliographic metadata (DOI, work title, year, citations and canonical URL) enters the learning pipeline.

## Small run without API secrets in source

With a registered polite-pool contact email set in your own terminal:

    export CROSSREF_CONTACT_EMAIL=YOUR_CONTACT_EMAIL
    python -m scripts.fetch_research_catalogues --out raw-research --start 2025-01-01 --end 2025-01-31 --page-size 50 --max-pages 1

The script requests **one page per source** by default, with deterministic JSONL page files and SHA-256 manifest. The manifest never stores API keys or contact email. For larger OpenAlex cursor pagination, register a free account and set `OPENALEX_API_KEY` locally; never commit the key. OpenAlex announced key requirements for deeper cursor paging and usage budgets in late 2026.

## Scaling path

Each invocation is bounded to 100 pages x 100 records per source. Partition by publication date/month and resume from an external checkpoint; upload partitioned JSONL into a Unity Catalog Volume to avoid GitHub binary storage. At scale, use official datasets or provider bulk export facilities rather than unlimited rate-limited page requests. Query quotas and provider fair-use restrictions apply.

## Spark processing

Upload `raw-research/openalex/` and `raw-research/crossref/` beneath a UC Volume folder. Run `notebooks/03_real_scholarly_metadata_lakehouse.py` with its `landing_root` widget set to that folder. It creates Bronze raw records, Silver quality quarantine, DOI-based cross-catalog deduplication and a lexical token index, then Gold yearly publication and term-frequency marts.

This is *real metadata retrieval*, not yet a full text RAG deployment. The existing synthetic ACL/vector-RAG evaluation notebooks remain available for retrieval-learning and access-control exercises.

**Not deployed:** No live OpenAlex/Crossref downloads, no Databricks workspace execution, no vector database and no LLM endpoint have been run by the assistant.
