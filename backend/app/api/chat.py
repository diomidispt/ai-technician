"""Chat endpoint — Server-Sent Events (SSE) streaming.

## The streaming contract (stable across phases)

`POST /api/chat` with `{"messages": [{"role": "user", "content": "..."}]}` returns an SSE
stream of named events:

  event: token   data: {"delta": "<text chunk>"}      # zero or more, in order
  event: done    data: {"citations": [...]}           # exactly one, terminal

Phase 1 streams a **canned** reply (no RAG). When the RAG core lands, only the generator in
`stream_answer()` changes — it will yield real token deltas from Claude and a populated
`citations` list (manual + page/section, per the golden rule). The frontend does not change.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


# Small delay between chunks so the UI visibly "types" like Claude.
_TOKEN_DELAY_SECONDS = 0.03


def _canned_reply(question: str) -> str:
    """Phase-1 placeholder response. Replaced by the RAG synthesizer in a later phase."""
    return (
        f"You asked: **{question}**\n\n"
        "This is the Jensen technical assistant UI demo. The chat, streaming, and markdown "
        "rendering all work end-to-end — but the RAG core is **not wired up yet**, so this "
        "reply is canned.\n\n"
        "Once retrieval lands, answers will:\n"
        "1. Come from the internal manual library first (web only as fallback).\n"
        "2. Carry source citations (manual + page/section).\n"
        "3. Surface safety precautions before any electrical/steam/high-temp step.\n"
    )


async def stream_answer(request: ChatRequest) -> AsyncGenerator[dict, None]:
    """Yield SSE events. Swap the body for the real RAG pipeline later — contract stays the same."""
    question = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "",
    )

    for word in _canned_reply(question).split(" "):
        yield {"event": "token", "data": json.dumps({"delta": word + " "})}
        await asyncio.sleep(_TOKEN_DELAY_SECONDS)

    # citations: empty in phase 1; populated by the RAG synthesizer later.
    yield {"event": "done", "data": json.dumps({"citations": []})}


@router.post("/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    return EventSourceResponse(stream_answer(request))
