# `app/db/` — data access layer

Postgres + pgvector access. All vector SQL lives here — **no raw SQL in route handlers**
(CLAUDE.md §Conventions). Locally this is a Docker Postgres; in AWS it becomes RDS.

- `models.py` — `Document` and `Chunk` (with a pgvector `Vector` embedding column).
- `session.py` — engine, session factory, and `init_db()` (creates the `vector` extension +
  tables; idempotent).
- `repository.py` — upsert documents, add chunks, and `search_chunks()` (top-k cosine search).

Conversation history + audit-log tables are added in a later phase.
