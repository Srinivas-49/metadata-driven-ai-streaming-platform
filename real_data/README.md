# Scientific evidence platform: Crossref + Europe PMC

**Official, public research metadata feeds:**
- Crossref REST API https://api.crossref.org/works — DOI identifiers, titles, publishers, publication dates and citation counts; its public metadata is generally reusable, but check record rights.
- Europe PMC REST API https://www.ebi.ac.uk/europepmc/webservices/rest/search — over 33 million indexed research publications. Restrict collection to **OPEN_ACCESS:Y** and inspect licence terms before reusing article abstracts. This project does **not** bulk-download full text.

The two API crawlers persist page files as JSON Lines, SHA-256 checksums, and cursor bookmarks. They merge records on normalised DOI and write an enriched citation-backed metadata collection. Sources can have **zero DOI overlap** for a particular query; this is a genuine matching-rate metric, not guaranteed success.

Run from a network-enabled machine:
```bash
python -m real_data.scholarly_sources --topic "data engineering" --pages 2 --page-size 25 --out real-data/scholarly
```
Change the topic to e.g. "machine learning" to obtain a larger corpus. Crawls over 10 pages require --confirm-large and a rate-limit/permissions review. Do NOT crawl millions of copyrighted abstracts or paid full text simply because a source API is public. Crossref public access has request and concurrency limits; Europe PMC prohibits bulk downloading other non-open-access content.

Upload only licensed and permission-reviewed files to a Databricks managed Volume, then use the Spark notebook to create curated metadata/chunks, citation indexes and evaluation. Free Edition restricts arbitrary outbound internet access, so laptop → Volume is the intended safe path.

Data rights and privacy: citations should link to canonical DOI pages; no claim of medical diagnosis accuracy, confidential indexing, or clinical compliance. No content from the APIs is committed into GitHub automatically; CI uses tiny fabricated mock records.

## Cursor-based deep backfill

For larger corpus experiments, use fixed topics and repeat page windows while retaining the same manifest files:

```bash
python -m real_data.scholarly_sources --topic "machine learning" --out real-data/research_ml --page-size 1000 --pages 10 --start-page 0
python -m real_data.scholarly_sources --topic "machine learning" --out real-data/research_ml --page-size 1000 --pages 10 --start-page 10 --confirm-large
```

The crawler verifies previous pages and resumes from the last persisted Crossref/Europe PMC cursor rather than naive offset pagination. Do not change topic or page size for a continuing crawl. Observe provider rate limits, use polite serial requests, and stop when an upstream cursor stops progressing. **Never treat an available large metadata corpus as permission to bulk copy copyrighted full texts.**
