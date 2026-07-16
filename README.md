# Jensen AI Technical Support Assistant

RAG assistant for field technicians servicing Jensen industrial laundry equipment.
Answers troubleshooting questions from an internal manual library first, web only as fallback.

> **Architecture diagram:** [`docs/architecture.md`](./docs/architecture.md).
> **Full architecture & decisions:** [`CLAUDE.md`](./CLAUDE.md).

## What runs today

A **real, local, $0 RAG assistant** with **login, roles, an admin console, and a web
fallback**. You sign in; ask troubleshooting questions; the assistant answers from the ingested
PDF manuals first (**with citations**), and only falls back to a web search when the library
doesn't cover it. Everything runs on your machine — no AWS, no API keys, no token cost:

- **Auth (local, simulates Cognito)** — JWT login + roles (**admin** / **technician**), instant
  disable (revocation) and access-expiry dates. Demo logins: `admin`/`admin`, `technician`/`technician`.
- **Admin console** — manage users, **upload & ingest PDFs** from the browser, view a **query
  audit log** (who asked what). Admins only.
- **Frontend** — React + Vite chat UI (streaming, markdown, Jensen branding, **🎤 voice input**).
- **Backend** — FastAPI: auth guard → retrieve (pgvector, HNSW) → sufficiency filter → ground →
  stream with **precise** citations; **web-search fallback** (DuckDuckGo) when the library is
  insufficient, clearly flagged as external.
- **Model** — [Ollama](https://ollama.com): `aya-expanse:8b` (answers) + `bge-m3` (embeddings).
  **Multilingual** (Greek + English). Metal-accelerated, free, offline.
- **Vector store** — Postgres + pgvector with an **HNSW** index (Docker). Same engine as RDS.

```
frontend (:5173) ─login─▶ backend (:8000): /api/auth · /api/admin · /api/chat
       │                        ├─▶ pgvector (:5432)   ← ingested PDFs, users, audit
       │                        ├─▶ Ollama (:11434, host)
       ▲                        └─▶ DuckDuckGo (fallback only)
       └──── SSE token stream + citations ◀───┘
```

## Run it

### 1. Install + start Ollama (one time)

```bash
brew install ollama
ollama serve &                       # leave running
ollama pull aya-expanse:8b
ollama pull bge-m3
```

### 2. Start the stack

```bash
make demo                            # frontend :5173, backend :8000, postgres :5432
```

### 3. Sign in and go

Open **http://localhost:5173** and sign in:
- **admin** / **admin** — chat **+** the admin console (users, document upload, audit log)
- **technician** / **technician** — chat only

**Ingest manuals** either from the **Admin → Library** tab (upload a PDF), or from the CLI:

```bash
make ingest                          # ingest every PDF in ingestion/sample_docs/
```

Ask about something in your PDFs (English or Greek). If the library doesn't cover it, the
assistant falls back to a **web search** (flagged as external) — set `WEB_FALLBACK_ENABLED=false`
to keep it fully offline.

> No Docker? Run Postgres yourself (or just the `postgres` service via
> `docker compose up -d postgres`), then `make backend-dev` and `make frontend-dev`, and
> `cd backend && python -m app.ingestion.run ../ingestion/sample_docs` to ingest.

## Repo layout

| Path          | Status | Purpose |
|---------------|--------|---------|
| `frontend/`   | ✅ runnable   | React SPA chat UI (Vite; static → S3/CloudFront in prod) |
| `backend/`    | ✅ runnable   | FastAPI: RAG core (`rag/`), data layer (`db/`), ingestion CLI (`ingestion/`) |
| `ingestion/`  | ✅ `sample_docs/` | Drop PDFs here; ingestion code lives in `backend/app/ingestion/` for now |
| `shared/`     | 🔲 placeholder | Schemas shared across services (pydantic ↔ TS types) |
| `infra/`      | 🔲 placeholder | Terraform (AWS resources, single env) |
| `docs/`       | 📄 reference  | Architecture diagram & decision records |

## What's still missing (next phases)

Auth (Cognito) · conversation history + audit logs · web-search fallback · admin console ·
AWS infra + deploy. See [`CLAUDE.md` §8](./CLAUDE.md) for the full build order. Swapping the
local Ollama model for Claude/Bedrock is a config change behind `app/rag/ollama_client.py`.

## Common commands

```bash
make demo                  # full local stack (docker compose)
make ingest                # ingest PDFs from ingestion/sample_docs
make down                  # stop the stack
pytest backend/tests       # backend unit tests (no DB/Ollama needed)
ruff check backend && ruff format backend
```
