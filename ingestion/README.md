# `ingestion/` — document ingestion pipeline (placeholder)

**Phase: ingestion (S3 → pgvector)** — see CLAUDE.md §8. Not yet implemented.

Reads documents **only from a private S3 bucket** (never OneDrive/Google directly). Own
Dockerfile → ECR `jensen/ingestion` → Lambda, EventBridge-triggered.

Pipeline (CLAUDE.md §2 Ingestion):
`EventBridge (schedule) → detect new/changed S3 objects → parse (PDF/Office) + Textract OCR
→ chunk (~500-1000 tokens on section boundaries) → embed (Titan) → upsert into pgvector`.

Shares chunking/embedding code with the backend — keep it in `shared/` or a common module.

Planned layout: `app/` (workers), `Dockerfile`, `tests/`, `pyproject.toml`.
