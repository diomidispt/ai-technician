"""RAG pipeline: retrieve internal chunks → ground the model → stream an answer with citations.

Internal-first is enforced *here in code* (CLAUDE.md golden rule): the web-search fallback runs
ONLY when no retrieved chunk is relevant enough — never before, and never mixed in. Web answers
are clearly flagged as external. Every answered question is written to the audit log.
"""

import json
import re
from collections.abc import AsyncIterator

from app.config import settings
from app.db.models import AuditLog
from app.db.repository import RetrievedChunk, search_chunks
from app.db.session import SessionLocal
from app.rag import ollama_client, websearch

# Greek + Coptic and Greek Extended blocks. Reliable enough to tell Greek from English.
_GREEK_CHARS = re.compile(r"[Ͱ-Ͽἀ-῿]")


def _detect_language(text: str) -> str:
    """Pick the answer language deterministically instead of trusting the model to detect it."""
    return "Greek" if _GREEK_CHARS.search(text) else "English"


_LANGUAGE_RULE = (
    "LANGUAGE: Write your ENTIRE reply in the SAME language as the QUESTION (English or Greek). "
    "The sources may be in another language; translate from them as needed."
)

INTERNAL_PROMPT = f"""You are the Jensen technical support assistant for field technicians \
servicing industrial laundry equipment.

Rules you MUST follow:
- {_LANGUAGE_RULE}
- Answer ONLY using the numbered CONTEXT passages provided. Do not use outside knowledge.
- If the context does not contain the answer, say so plainly and recommend escalation. \
Never guess part numbers, torque values, or error-code meanings.
- Safety first: if a step involves electrical, steam, high-temperature, or moving parts, \
state the safety precaution BEFORE the repair step.
- Cite the passages you used inline like [1], [2] matching the CONTEXT numbers.
- Be concise and practical. Use short steps."""

WEB_PROMPT = f"""You are the Jensen technical support assistant. The internal manual library \
did NOT cover this question, so you are answering from a WEB SEARCH.

Rules you MUST follow:
- {_LANGUAGE_RULE}
- Begin with one short sentence stating this answer is from a web search, not the internal \
Jensen manuals, and should be verified.
- Answer using ONLY the numbered web RESULTS provided. Cite them inline like [1], [2].
- Safety first for any electrical/steam/high-temp/moving-part step.
- Be concise."""


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
    cover it -> web fallback / refuse). Otherwise keeps chunks within `relevance_margin` of the
    best match so we ground on and cite the relevant pages, not loosely-related ones.
    """
    if not hits or hits[0].distance > settings.sufficiency_max_distance:
        return []
    cutoff = hits[0].distance + settings.relevance_margin
    return [h for h in hits if h.distance <= cutoff]


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


def _record_audit(user_email: str, question: str, source: str) -> None:
    session = SessionLocal()
    try:
        session.add(AuditLog(user_email=user_email, question=question, source=source))
        session.commit()
    finally:
        session.close()


async def run(question: str, user_email: str) -> AsyncIterator[dict]:
    """Yield SSE events (`token` deltas then a terminal `done` carrying source + citations)."""
    language = _detect_language(question)

    # 1. Internal library first.
    query_embedding = await ollama_client.embed(question)
    session = SessionLocal()
    try:
        hits = search_chunks(session, query_embedding, settings.retrieval_top_k)
    finally:
        session.close()
    relevant = _select_relevant(hits)

    if relevant:
        context = _build_context(relevant)
        messages = [
            {"role": "system", "content": INTERNAL_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\n"
             f"Write your entire answer in {language}."},
        ]
        async for delta in ollama_client.chat_stream(messages):
            yield _sse("token", {"delta": delta})
        _record_audit(user_email, question, "internal")
        yield _sse("done", {"source": "internal", "citations": _citations(relevant)})
        return

    # 2. Web-search fallback (only because the library was insufficient).
    if settings.web_fallback_enabled:
        results = await websearch.search(question)
        if results:
            numbered = "\n\n".join(
                f"[{i}] {r.title}\n{r.snippet}\n({r.url})" for i, r in enumerate(results, start=1)
            )
            messages = [
                {"role": "system", "content": WEB_PROMPT},
                {"role": "user", "content": f"WEB RESULTS:\n{numbered}\n\nQUESTION: {question}\n\n"
                 f"Write your entire answer in {language}."},
            ]
            async for delta in ollama_client.chat_stream(messages):
                yield _sse("token", {"delta": delta})
            _record_audit(user_email, question, "web")
            citations = [{"title": r.title, "url": r.url} for r in results]
            yield _sse("done", {"source": "web", "citations": citations})
            return

    # 3. Nothing internal, no web result — refuse honestly.
    msg = (
        "I couldn't find this in the internal manual library"
        + (" or on the web" if settings.web_fallback_enabled else "")
        + ", so I can't answer it reliably. Please rephrase, or escalate to engineering."
    )
    for word in msg.split(" "):
        yield _sse("token", {"delta": word + " "})
    _record_audit(user_email, question, "none")
    yield _sse("done", {"source": "none", "citations": []})
