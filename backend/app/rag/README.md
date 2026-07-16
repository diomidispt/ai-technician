# `app/rag/` — RAG core

The internal-first retrieval + generation pipeline.

- `ollama_client.py` — the only code that talks to the model provider (embeddings + streaming
  chat). Swap for a Claude/Bedrock client later with the same methods; nothing else changes.
- `chunking.py` — split page text into embed-sized, overlapping chunks (keeps page numbers).
- `pipeline.py` — the flow: embed query → `search_chunks` (pgvector) → **sufficiency check** →
  if insufficient, say so + recommend escalation; else synthesize from ONLY those chunks and
  stream tokens, returning citations.

**Golden rules enforced here in code:** internal library first (no answering from general
knowledge when retrieval is insufficient), every answer carries citations, safety-first in the
system prompt. Web-search fallback is a later phase — locally, "insufficient" ends the flow.

Wire-in point: `app/api/chat.py` calls `pipeline.run()` and streams its SSE events.
