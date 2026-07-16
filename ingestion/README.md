# `ingestion/` — document ingestion

Turns PDFs into searchable, embedded chunks in pgvector.

- **`sample_docs/`** — drop your PDF manuals here (git-ignored). Text-based PDFs work best.
- The ingestion **code** currently lives in the backend package (`backend/app/ingestion/`) so
  it shares the DB + embedding code directly. It will be split into its own deployable
  (own Dockerfile → Lambda, EventBridge-triggered, reading from S3 + Textract OCR) when the
  cloud phase lands — see CLAUDE.md §2 (Ingestion).

## Run (local)

With the stack up (`make demo`) and Ollama running:

```bash
make ingest        # ingests every PDF in ingestion/sample_docs/ into pgvector
```

Under the hood: `python -m app.ingestion.run /docs` — parse (pypdf) → chunk → embed
(`bge-m3` via Ollama) → upsert into Postgres. Re-running replaces a file's chunks
(idempotent per filename).
