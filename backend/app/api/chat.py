"""Chat endpoint — authenticated, Server-Sent Events (SSE) streaming.

`POST /api/chat` (requires a bearer token) with `{"messages": [...], "conversation_id"?: int}`
returns an SSE stream:

  event: token   data: {"delta": "<text chunk>"}
  event: done    data: {"source": "internal|web|none", "citations": [...], "conversation_id": int}

The turn is persisted to the user's conversation history: the incoming user message up front (a new
thread is created + pruned to the retention cap if no conversation_id is given), and the assistant
message — with its source + citations — once the stream completes. Citations are `{manual, page,
section}` for internal answers and `{title, url}` for web-fallback answers.
"""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import repository
from app.db.models import User
from app.db.session import SessionLocal
from app.rag import pipeline

router = APIRouter()


@router.get("/meta")
async def meta() -> dict:
    """What the UI shows about the running system (which model answers, web fallback on/off)."""
    return {
        "answer_model": settings.answer_model,
        "embed_model": settings.embed_model,
        "web_fallback": settings.web_fallback_enabled,
    }


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    conversation_id: int | None = None


def _open_conversation(user_email: str, conversation_id: int | None, question: str) -> int:
    """Resolve the conversation to append to, persist the user's message, return its id.

    Creates + prunes a new thread when there's no (owned) conversation_id.
    """
    session = SessionLocal()
    try:
        if conversation_id is None or not repository.owns_conversation(
            session, conversation_id, user_email
        ):
            conv = repository.create_conversation(
                session, user_email, repository.make_title(question)
            )
            conversation_id = conv.id
            repository.prune_conversations(session, user_email, settings.history_max_conversations)
        repository.add_message(session, conversation_id, "user", question)
        session.commit()
        return conversation_id
    finally:
        session.close()


def _save_answer(conversation_id: int, content: str, source: str, citations: list) -> None:
    session = SessionLocal()
    try:
        repository.add_message(session, conversation_id, "assistant", content, source, citations)
        session.commit()
    finally:
        session.close()


@router.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)) -> EventSourceResponse:
    history = [{"role": m.role, "content": m.content} for m in request.messages]
    question = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    conversation_id = _open_conversation(user.email, request.conversation_id, question)

    async def persisted_stream() -> AsyncIterator[dict]:
        parts: list[str] = []
        source, citations = "none", []
        async for event in pipeline.run(history, user.email):
            if event["event"] == "token":
                parts.append(json.loads(event["data"]).get("delta", ""))
                yield event
            elif event["event"] == "done":
                done = json.loads(event["data"])
                source, citations = done.get("source", "none"), done.get("citations", [])
                done["conversation_id"] = conversation_id
                yield {"event": "done", "data": json.dumps(done)}
            else:
                yield event
        _save_answer(conversation_id, "".join(parts), source, citations)

    return EventSourceResponse(persisted_stream())
