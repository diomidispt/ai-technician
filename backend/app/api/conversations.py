"""Per-user chat history API — the backend for the conversation sidebar.

Every route is scoped to the signed-in user (`user_email`), so a user only ever sees, opens, or
deletes their own threads. Local stand-in for the RDS conversations table.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import repository
from app.db.models import User
from app.db.session import get_session

router = APIRouter()


class ConversationSummary(BaseModel):
    id: int
    title: str
    updated_at: datetime


class MessageOut(BaseModel):
    role: str
    content: str
    source: str | None = None
    citations: list | None = None


class ConversationDetail(BaseModel):
    id: int
    title: str
    messages: list[MessageOut]


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> list[ConversationSummary]:
    convs = repository.list_conversations(session, user.email, settings.history_max_conversations)
    return [ConversationSummary(id=c.id, title=c.title, updated_at=c.updated_at) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversationDetail:
    conv = repository.get_conversation(session, conversation_id, user.email)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        messages=[
            MessageOut(role=m.role, content=m.content, source=m.source, citations=m.citations)
            for m in conv.messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    deleted = repository.delete_conversation(session, conversation_id, user.email)
    session.commit()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
