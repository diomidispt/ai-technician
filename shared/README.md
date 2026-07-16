# `shared/` — cross-service schemas (placeholder)

**Phase: alongside RAG/ingestion** — see CLAUDE.md §Repo layout. Not yet populated.

Schemas/types shared across services: pydantic models used by `backend/` and `ingestion/`,
and their TypeScript equivalents consumed by `frontend/`. Chunking/embedding code shared
between backend and ingestion also belongs here (or a common module).

Keep this the single source of truth for the chat/message/citation shapes so the
`/api/chat` contract stays consistent across the stack.
