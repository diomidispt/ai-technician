"""Chat endpoint — Server-Sent Events (SSE) streaming.

## The streaming contract

`POST /api/chat` with `{"messages": [{"role": "user", "content": "..."}]}` returns an SSE
stream of named events:

  event: token   data: {"delta": "<text chunk>"}      # zero or more, in order
  event: done    data: {"citations": [{"manual","page"}]}   # exactly one, terminal

The answer is produced by the RAG pipeline (`app/rag/pipeline.py`): retrieve internal chunks
→ ground the local model → stream tokens → return citations. Internal-first + citations are
enforced in code (CLAUDE.md golden rules).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.rag import pipeline

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@router.post("/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    question = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "",
    )
    return EventSourceResponse(pipeline.run(question))
