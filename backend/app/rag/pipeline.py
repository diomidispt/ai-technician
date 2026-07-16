"""RAG pipeline: retrieve internal chunks → ground the model → stream an answer with citations.

Internal-first is enforced *here in code* (CLAUDE.md golden rule): if no retrieved chunk is
relevant enough, we say the library doesn't cover it and recommend escalation — we do NOT let
the model answer from general knowledge. (Web-search fallback is a later phase; locally there
is none, so "not sufficient" ends the flow honestly.)
"""

import json
import re
from collections.abc import AsyncIterator

from app.config import settings
from app.db.repository import RetrievedChunk, search_chunks
from app.db.session import SessionLocal
from app.rag import ollama_client

# Greek + Coptic and Greek Extended blocks. Reliable enough to tell Greek from English.
_GREEK_CHARS = re.compile(r"[Ͱ-Ͽἀ-῿]")


def _detect_language(text: str) -> str:
    """Pick the answer language deterministically instead of trusting the model to detect it."""
    return "Greek" if _GREEK_CHARS.search(text) else "English"

SYSTEM_PROMPT = """You are the Jensen technical support assistant for field technicians \
servicing industrial laundry equipment.

Rules you MUST follow:
- LANGUAGE: Write your ENTIRE reply in the SAME language as the QUESTION. If the question is \
in English, answer in English. If it is in Greek, answer in Greek. Match the question's \
language exactly — the CONTEXT may be in a different language; translate from it as needed.
- Answer ONLY using the numbered CONTEXT passages provided. Do not use outside knowledge.
- If the context does not contain the answer, say so plainly and recommend escalation. \
Never guess part numbers, torque values, or error-code meanings.
- Safety first: if a step involves electrical, steam, high-temperature, or moving parts, \
state the safety precaution BEFORE the repair step.
- Cite the passages you used inline like [1], [2] matching the CONTEXT numbers.
- Be concise and practical. Use short steps."""


def _build_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(f"[{i}] (source: {c.filename}, page {c.page})\n{c.content}")
    return "\n\n".join(blocks)


def _citations(chunks: list[RetrievedChunk]) -> list[dict]:
    seen, out = set(), []
    for c in chunks:
        key = (c.filename, c.page)
        if key not in seen:
            seen.add(key)
            out.append({"manual": c.filename, "page": c.page})
    return out


def _select_relevant(hits: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Internal-first selection. `hits` is ordered by ascending distance.

    Returns [] when even the closest chunk is beyond the sufficiency gate (library doesn't
    cover it -> refuse). Otherwise keeps chunks within `relevance_margin` of the best match so
    we ground on and cite the relevant pages, not loosely-related ones.
    """
    if not hits or hits[0].distance > settings.sufficiency_max_distance:
        return []
    cutoff = hits[0].distance + settings.relevance_margin
    return [h for h in hits if h.distance <= cutoff]


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


async def run(question: str) -> AsyncIterator[dict]:
    """Yield SSE events (`token` deltas then a terminal `done` carrying citations)."""
    # 1. Embed the question and search the internal library.
    query_embedding = await ollama_client.embed(question)
    session = SessionLocal()
    try:
        hits = search_chunks(session, query_embedding, settings.retrieval_top_k)
    finally:
        session.close()

    # 2. Sufficiency + relevance selection (internal-first).
    relevant = _select_relevant(hits)

    if not relevant:
        msg = (
            "I couldn't find this in the internal manual library, so I can't answer it "
            "reliably. Please rephrase, or escalate to engineering.\n\n"
            "_(Tip: ingest the relevant manual so I can answer from it.)_"
        )
        for word in msg.split(" "):
            yield _sse("token", {"delta": word + " "})
        yield _sse("done", {"citations": []})
        return

    # 3. Synthesize from ONLY the retrieved chunks, streaming tokens as they arrive.
    context = _build_context(relevant)
    language = _detect_language(question)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\n"
                f"Write your entire answer in {language}."
            ),
        },
    ]
    async for delta in ollama_client.chat_stream(messages):
        yield _sse("token", {"delta": delta})

    yield _sse("done", {"citations": _citations(relevant)})
