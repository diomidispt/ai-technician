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
from app.db.repository import RetrievedChunk, _rrf_fuse, keyword_search, vector_search
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
- If the results are NOT clearly about Jensen or industrial laundry equipment (e.g. they are about \
unrelated appliances or brands like printers or dishwashers), do NOT use them: say you couldn't \
find relevant information on the web and recommend escalating to Jensen engineering.
- Safety first for any electrical/steam/high-temp/moving-part step.
- Be concise."""


def _build_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = f"page {c.page}"
        if c.section:
            loc += f", section {c.section}"
        blocks.append(f"[{i}] (source: {c.filename}, {loc})\n{c.content}")
    return "\n\n".join(blocks)


def _citations(chunks: list[RetrievedChunk]) -> list[dict]:
    seen, out = set(), []
    for c in chunks:
        key = (c.filename, c.page, c.section)
        if key not in seen:
            seen.add(key)
            cite: dict = {"manual": c.filename, "page": c.page}
            if c.section:
                cite["section"] = c.section
            out.append(cite)
    return out


def _select_relevant(
    vector_hits: list[RetrievedChunk], keyword_hits: list[RetrievedChunk] | None = None
) -> list[RetrievedChunk]:
    """Internal-first selection. `vector_hits` is ordered by ascending distance.

    The sufficiency gate stays vector-based: if even the closest chunk by MEANING is beyond the
    gate, the library doesn't cover it (-> web fallback / refuse). This keeps internal-first
    behaviour identical regardless of hybrid fusion. When `keyword_hits` are supplied, the passing
    chunks are re-ordered by RRF (vector + keyword). Otherwise (vector-only) we keep chunks within
    `relevance_margin` of the best match so we cite relevant pages, not loosely-related ones.
    """
    if not vector_hits or vector_hits[0].distance is None:
        return []
    if vector_hits[0].distance > settings.sufficiency_max_distance:
        return []
    if keyword_hits:
        return _rrf_fuse(vector_hits, keyword_hits, settings.rrf_k, settings.retrieval_top_k)
    cutoff = vector_hits[0].distance + settings.relevance_margin
    near = [h for h in vector_hits if h.distance is not None and h.distance <= cutoff]
    return near[: settings.retrieval_top_k]


# One call does both jobs: "does this even need the PDFs?" (router — without it, greetings get
# answered from random chunks) and, for technical follow-ups, rewriting into a standalone
# retrieval query (e.g. "and the WE110?" -> "WE110 <prior topic>"). Merged into a single call on
# the answer model (rather than a router call + a separate rewrite call on a different small
# model) so routing stays multilingual-accurate — a small English-tuned model was found to
# misroute Greek technical questions as chitchat — and each message costs one round trip and one
# resident model instead of two.
ROUTE_PROMPT = (
    "You route a technician's LATEST message for a support assistant for Jensen industrial "
    "laundry equipment, and rewrite it into a standalone search query for the manual database.\n"
    'Return ONLY compact JSON, no other text: {"intent": "TECHNICAL"|"CHITCHAT", '
    '"query": "<standalone search query>"}\n'
    "TECHNICAL: a troubleshooting, repair, maintenance, product, error-code, part, or how-to "
    "question about the equipment — including short follow-ups that refer to a model, part, or "
    "the prior technical topic (e.g. 'and the WE110?').\n"
    "CHITCHAT: greetings, thanks, small talk, or questions about you/the assistant "
    "(e.g. 'hello', 'thanks', 'who are you?').\n"
    "For the query field: resolve pronouns and implicit references (equipment models, error "
    "codes, parts) using the conversation. Keep the original language. For CHITCHAT, set query "
    "to the latest message unchanged."
)

CHITCHAT_PROMPT = """You are the Jensen technical support assistant for field technicians \
servicing industrial laundry equipment. The user's message is small talk or is not about the \
equipment.

- {language_rule}
- If they greet or thank you, reply warmly in one short sentence.
- If they ask about anything UNRELATED to industrial laundry equipment (general knowledge, trivia,
  other topics), politely say it's outside what you can help with — do NOT answer the question.
- Always invite them to ask a troubleshooting question about the equipment.
- Keep it to one or two short sentences. Do NOT invent technical details, part numbers, or steps,
  and do NOT cite any manual."""


def _split_history(history: list[dict]) -> tuple[list[dict], str]:
    """Return (prior turns, current question). The question is the last user message."""
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "user":
            return history[:i], history[i].get("content", "")
    return [], ""


def _recent_turns(prior: list[dict]) -> list[dict]:
    """The last `history_max_turns` prior messages, as clean {role, content} dicts."""
    turns = [
        {"role": m["role"], "content": m["content"]}
        for m in prior
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    return turns[-settings.history_max_turns :]


def _parse_route(text: str, question: str) -> tuple[str, str]:
    """Parse the router+rewrite JSON reply into (intent, query).

    Fails open to ('technical', question) on any hiccup — malformed JSON, missing fields, or a
    runaway (chatty) reply — so a real question is never dropped or left unsearchable.
    """
    try:
        data = json.loads(text.strip().strip("`"))
        intent = "chitchat" if str(data.get("intent", "")).upper() == "CHITCHAT" else "technical"
        query = data.get("query")
        if not isinstance(query, str) or not query.strip() or len(query) > 300:
            query = question
        return intent, query
    except Exception:
        return "technical", question


async def _route_and_rewrite(prior: list[dict], question: str) -> tuple[str, str]:
    """One LLM call: classify the message ('technical'/'chitchat') AND, for follow-ups, rewrite it
    into a standalone retrieval query — replacing two separate calls to two different local
    models with one. Recent turns disambiguate short follow-ups and resolve references.
    """
    if not settings.intent_router_enabled and not settings.query_rewrite_enabled:
        return "technical", question
    turns = _recent_turns(prior)
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in turns)
    user = (f"Conversation so far:\n{convo}\n\n" if convo else "") + (
        f"Latest message: {question}\n\nJSON:"
    )
    messages = [
        {"role": "system", "content": ROUTE_PROMPT},
        {"role": "user", "content": user},
    ]
    try:
        reply = await ollama_client.chat(messages)
    except Exception:  # router/rewrite hiccup — default to searching the manuals as asked.
        return "technical", question
    intent, query = _parse_route(reply, question)
    if not settings.intent_router_enabled:
        intent = "technical"
    # Only trust the rewrite when there's a conversation to resolve. On a first message there's
    # nothing to disambiguate, and paraphrasing tends to genericize a specific question (measured:
    # it can push embedding distance from a well-matched chunk to a worse one) — so the original
    # wording wins by default.
    if not settings.query_rewrite_enabled or not turns:
        query = question
    return intent, query


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


def _record_audit(user_email: str, question: str, source: str) -> None:
    session = SessionLocal()
    try:
        session.add(AuditLog(user_email=user_email, question=question, source=source))
        session.commit()
    finally:
        session.close()


async def run(history: list[dict], user_email: str) -> AsyncIterator[dict]:
    """Yield SSE events (`token` deltas then a terminal `done` carrying source + citations).

    `history` is the full conversation ({role, content}); the last user message is the question.
    Prior turns give the model context and drive a history-aware retrieval-query rewrite.
    """
    prior, question = _split_history(history)
    language = _detect_language(question)

    # 0. Router + rewrite in one call: does this message even need the manuals, and if so, what's
    #    its standalone retrieval query? Greetings / small talk get a natural reply with NO
    #    retrieval — so "hello" never gets answered from a random PDF chunk. Technical questions
    #    fall through to the retrieval flow below with a history-aware search query already in hand.
    intent, search_query = await _route_and_rewrite(prior, question)
    if intent == "chitchat":
        rule = "Reply in Greek." if language == "Greek" else "Reply in English."
        messages = [
            {"role": "system", "content": CHITCHAT_PROMPT.format(language_rule=rule)},
            *_recent_turns(prior),
            {"role": "user", "content": question},
        ]
        async for delta in ollama_client.chat_stream(messages):
            yield _sse("token", {"delta": delta})
        _record_audit(user_email, question, "chat")
        yield _sse("done", {"source": "chat", "citations": []})
        return

    # 1. Internal library first. Vector (meaning) + keyword (exact tokens); the sufficiency gate
    #    stays vector-based, RRF just re-orders the passing chunks.
    query_embedding = await ollama_client.embed(search_query)
    session = SessionLocal()
    try:
        if settings.hybrid_enabled:
            vector_hits = vector_search(session, query_embedding, settings.retrieval_candidate_k)
            keyword_hits = keyword_search(session, search_query, settings.retrieval_candidate_k)
        else:
            vector_hits = vector_search(session, query_embedding, settings.retrieval_top_k)
            keyword_hits = []
    finally:
        session.close()
    relevant = _select_relevant(vector_hits, keyword_hits)

    if relevant:
        context = _build_context(relevant)
        messages = [
            {"role": "system", "content": INTERNAL_PROMPT},
            *_recent_turns(prior),
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\n"
                f"Write your entire answer in {language}.",
            },
        ]
        async for delta in ollama_client.chat_stream(messages):
            yield _sse("token", {"delta": delta})
        _record_audit(user_email, question, "internal")
        yield _sse("done", {"source": "internal", "citations": _citations(relevant)})
        return

    # 2. Web-search fallback (only because the library was insufficient). Search the standalone
    #    (history-aware) query, scoped to the equipment domain so results stay on-topic instead of
    #    pulling unrelated hits (e.g. a bare "E4" -> HP-printer results).
    if settings.web_fallback_enabled:
        scoped_query = f"{settings.web_search_scope} {search_query}".strip()
        results = await websearch.search(scoped_query)
        if results:
            numbered = "\n\n".join(
                f"[{i}] {r.title}\n{r.snippet}\n({r.url})" for i, r in enumerate(results, start=1)
            )
            messages = [
                {"role": "system", "content": WEB_PROMPT},
                {
                    "role": "user",
                    "content": f"WEB RESULTS:\n{numbered}\n\nQUESTION: {question}\n\n"
                    f"Write your entire answer in {language}.",
                },
            ]
            async for delta in ollama_client.chat_stream(messages):
                yield _sse("token", {"delta": delta})
            _record_audit(user_email, question, "web")
            citations = [{"title": r.title, "url": r.url} for r in results]
            yield _sse("done", {"source": "web", "citations": citations})
            return

    # 3. Nothing internal, no web result — refuse honestly (in the question's language).
    if language == "Greek":
        msg = (
            "Δεν το βρήκα στα εγχειρίδια"
            + (" ούτε στο web" if settings.web_fallback_enabled else "")
            + ", οπότε δεν μπορώ να απαντήσω αξιόπιστα. Δοκιμάστε να το διατυπώσετε αλλιώς ή "
            "απευθυνθείτε στο τμήμα μηχανικής."
        )
    else:
        msg = (
            "I couldn't find this in the internal manual library"
            + (" or on the web" if settings.web_fallback_enabled else "")
            + ", so I can't answer it reliably. Please rephrase, or escalate to engineering."
        )
    for word in msg.split(" "):
        yield _sse("token", {"delta": word + " "})
    _record_audit(user_email, question, "none")
    yield _sse("done", {"source": "none", "citations": []})
