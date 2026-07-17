"""Chat endpoint — authenticated, Server-Sent Events (SSE) streaming.

`POST /api/chat` (requires a bearer token) with `{"messages": [{"role","content"}]}` returns
an SSE stream:

  event: token   data: {"delta": "<text chunk>"}
  event: done    data: {"source": "internal|web|none", "citations": [...]}

Citations are `{manual, page}` for internal answers and `{title, url}` for web-fallback answers.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import User
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


@router.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)) -> EventSourceResponse:
    question = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "",
    )
    return EventSourceResponse(pipeline.run(question, user.email))
