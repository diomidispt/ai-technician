# `app/db/` — data access layer (placeholder)

**Phase: ingestion / RAG core** (see CLAUDE.md §8).

All vector queries and conversation/audit-log access go through this layer — **no raw SQL
scattered in route handlers** (CLAUDE.md §Conventions). Backs onto RDS PostgreSQL + pgvector
(one DB: embeddings, chunk text, metadata, conversations, audit logs).
