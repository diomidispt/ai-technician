# `app/rag/` — RAG core (placeholder)

**Phase: RAG core** (after ingestion; see CLAUDE.md §8).

The internal-first retrieval pipeline lives here. Per-query flow (CLAUDE.md §2 Backend):

1. Embed the (optionally rewritten) query.
2. Vector search in pgvector → top-k chunks (via `app/db/`, never raw SQL in routes).
3. Rerank + sufficiency check.
4. If sufficient → synthesize with Claude using ONLY those chunks, **with citations**.
5. If not → web-search fallback, clearly flagged as external.

**Golden rule:** internal-first ordering is enforced *in code here* (step 5 runs only if
step 4 fails), never left to the model. Every answer carries citations.

Wire-in point: `stream_answer()` in `app/api/chat.py` calls into this module and yields the
same `token` / `done` SSE events the frontend already consumes.
