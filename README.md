# Jensen AI Technical Support Assistant

RAG assistant for field technicians servicing Jensen industrial laundry equipment.
Answers troubleshooting questions from an internal manual library first, web only as fallback.

> **Architecture diagram:** [`docs/architecture.md`](./docs/architecture.md).
> **Full architecture & decisions:** [`CLAUDE.md`](./CLAUDE.md).

## What runs today

A **real, local, $0 RAG assistant**. You ingest PDF manuals; the assistant retrieves the
relevant passages and answers **only** from them, with **citations** (file + page). Everything
runs on your machine — no AWS, no API keys, no token cost:

- **Frontend** — React + Vite chat UI (streaming, markdown, Jensen branding).
- **Backend** — FastAPI: retrieve (pgvector) → ground → stream the answer with citations.
- **Model** — [Ollama](https://ollama.com) on your Mac: `llama3.1:8b` (answers) +
  `nomic-embed-text` (embeddings). Metal-accelerated, free, offline.
- **Vector store** — Postgres + pgvector (Docker). Same engine as the AWS design (RDS), local.

```
frontend (:5173) ─POST /api/chat─▶ backend (:8000) ─┬─▶ pgvector (:5432)  ← ingested PDFs
       ▲                                             └─▶ Ollama (:11434, on host)
       └──────────── SSE token stream + citations ◀──┘
```

## Run it

### 1. Install + start Ollama (one time)

```bash
brew install ollama
ollama serve &                       # leave running
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 2. Start the stack

```bash
make demo                            # frontend :5173, backend :8000, postgres :5432
```

### 3. Ingest some manuals

Drop text-based PDFs into [`ingestion/sample_docs/`](./ingestion/sample_docs/), then:

```bash
make ingest                          # parse → chunk → embed → pgvector
```

Open **http://localhost:5173** and ask about something in your PDFs. If the library doesn't
cover a question, the assistant says so and recommends escalation — it won't make things up.

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
