# Jensen AI Technical Support Assistant

RAG assistant for field technicians servicing Jensen industrial laundry equipment.
Answers troubleshooting questions from an internal manual library first, web only as fallback.

> **Architecture diagram:** [`docs/architecture.md`](./docs/architecture.md).
> **Full architecture & decisions:** [`CLAUDE.md`](./CLAUDE.md).
> This README covers the repo layout and how to run the **Phase 1 chat demo**.

## What runs today (Phase 1)

A localhost chat that **looks and feels like Claude/ChatGPT** — streaming message bubbles,
markdown, Jensen branding. There is **no RAG, auth, or database yet**: the backend streams a
canned reply. The point is to lock in the real frontend↔backend streaming contract so the RAG
core drops in later behind the same `/api/chat` endpoint without the UI changing.

```
frontend (Vite/React, :5173)  ──POST /api/chat──▶  backend (FastAPI, :8000)
        ▲                                                   │
        └────────────── SSE token stream ◀──────────────────┘
```

## Run the demo

### Option A — Docker (matches the intended local stack)

```bash
make demo          # docker compose up  → frontend on http://localhost:5173
```

### Option B — no Docker

```bash
# terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Open http://localhost:5173, type a question, watch the answer stream in token-by-token.

## Repo layout

| Path          | Status (Phase 1) | Purpose |
|---------------|------------------|---------|
| `frontend/`   | ✅ runnable      | React SPA chat UI (Vite, static → S3/CloudFront in prod) |
| `backend/`    | ✅ runnable      | FastAPI RAG orchestrator (SSE streaming stub for now) |
| `ingestion/`  | 🔲 placeholder   | S3 → parse → chunk → embed → pgvector workers |
| `shared/`     | 🔲 placeholder   | Schemas shared across services (pydantic ↔ TS types) |
| `infra/`      | 🔲 placeholder   | Terraform modules + per-env composition |
| `docs/`       | 📄 reference     | Architecture & decision records |

## Build order

See [`CLAUDE.md` §8](./CLAUDE.md). Phase 1 (this) = **chat UI over a streaming stub**. Next:
Cognito auth → ingestion (S3→pgvector) → RAG core → web fallback → admin console.

## Common commands

```bash
make demo                  # full local stack via docker compose
pytest backend/tests       # backend tests
ruff check backend && ruff format backend
cd frontend && npm run dev # Vite dev server
cd frontend && npm run build
```
