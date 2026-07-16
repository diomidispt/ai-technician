# Architecture & Decisions

The authoritative narrative lives in [`../CLAUDE.md`](../CLAUDE.md) (§1–§8). This file holds
the **architecture diagram** and **decision records**.

## Diagram

Renders on GitHub (Mermaid). It mirrors the reference sketch, with one correction noted below.

```mermaid
flowchart TB
    UI["Web app · Chat + Admin (React)"]
    Cognito["Amazon Cognito<br/>roles · instant revocation"]
    RAG["RAG Orchestrator · FastAPI<br/>1 library search · 2 sufficiency check<br/>3 synthesize + citations · 4 web only as fallback"]
    Claude["Claude on Bedrock<br/>Sonnet = answers · Haiku = routing"]
    Web["Web Search<br/>fallback only (step 5)"]
    DB[("RDS + pgvector<br/>index · conversations · audit logs")]

    UI -- query --> RAG
    UI --> Cognito
    RAG --> Claude
    RAG -. fallback .-> Web
    RAG -- top-k --> DB

    subgraph ingestion["Ingestion — library sync (read-only)"]
        direction LR
        S3["S3 bucket<br/>(documents)"]
        Parse["Parsing<br/>PDF · Office · OCR · vision"]
        Embed["Chunk + Embed<br/>index update"]
        S3 --> Parse --> Embed
    end

    Drive["Google Drive / OneDrive"] -.->|pushed by client| S3
    Embed --> DB
```

### Correction vs the reference sketch
The reference sketch drew **Google Drive / OneDrive** as direct ingestion sources. Per the
decision in [`CLAUDE.md` §2 (Ingestion)](../CLAUDE.md), the system **never connects to
OneDrive/Google directly** — documents are pushed into a private **S3 bucket**, and ingestion
reads **only** from S3. The diagram reflects that: Drive/OneDrive feed *into* S3 (by whatever
sync the client chooses); nothing in our stack holds credentials to their tenant.

> Model names are illustrative — exact Bedrock model IDs are configuration, not architecture.

## What runs today (local, $0)
Almost the whole diagram is live end-to-end on your machine — each cloud box has a local stand-in:
- **Web app** = React chat **+ admin console**, behind a **login** (roles: admin / technician).
- **Cognito** = local JWT auth (`app/auth/`): roles, instant disable, access-expiry — same
  route guards Cognito would sit behind.
- **RAG Orchestrator** = FastAPI locally (not Lambda yet).
- **Claude on Bedrock** = **Ollama** (`aya-expanse:8b` + `bge-m3`, multilingual) behind a
  swappable client — $0, offline.
- **Web Search** fallback = **DuckDuckGo** (no key), runs only when the library is insufficient.
- **RDS + pgvector** = **Postgres + pgvector in Docker** (chunks **+ users + audit log**).
- **Ingestion** = admin uploads a PDF (or a local folder) → **pypdf** → chunk → embed (no S3/Textract yet).

Still cloud-only: real Cognito, RDS, S3+Textract ingestion, and all AWS infra. The app logic is
unchanged — only the backing services differ.

## Decision records

### ADR-0001 — Phase 1: chat UI over a streaming stub
- **Status:** accepted (2026-07)
- **Context:** first deliverable is a demoable, Claude-like chat. RAG/auth/DB are later phases.
- **Decision:** ship `frontend/` (minimal custom React) + `backend/` (FastAPI) with a
  **canned SSE reply**. Lock the `/api/chat` streaming contract (`token` deltas → `done`
  event) now so the RAG core plugs in behind it later without frontend changes.
- **Consequences:** no AWS dependency to demo; the citation UI slot exists but is empty until
  retrieval returns citations.

### ADR-0002 — Single environment, minimal DevOps surface
- **Status:** accepted (2026-07)
- **Context:** this is one application for one company (Jensen), not a multi-tenant product.
- **Decision:** **one environment** (no dev/prod split), **one Dockerfile per service**, and
  DevOps kept to two places — `.github/workflows/` (CI: one per service) and `infra/` (all AWS
  resources, flat). No elaborate release/branching strategy.
- **Consequences:** simpler to reason about and operate; if a staging environment is ever
  needed, it can be added later without reshaping the repo.

<!-- Add further ADRs here (auth model, embedding choice, rerank strategy, …). -->
