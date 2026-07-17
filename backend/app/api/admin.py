"""Admin console API (admins only): manage users, curate the document library, view audit.

Local stand-in for the Cognito admin actions + the S3/Drive upload + the RDS audit tables.
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.security import hash_password
from app.config import settings
from app.db.models import AuditLog, Chunk, Document, User
from app.db.session import get_session, init_db
from app.ingestion.run import ingest_file

router = APIRouter(dependencies=[Depends(require_admin)])


# ---------------- Users ----------------
class UserRow(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    access_expires: datetime | None


class CreateUser(BaseModel):
    email: str
    password: str
    role: str = "technician"
    access_expires: datetime | None = None


class UpdateUser(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    access_expires: datetime | None = None
    password: str | None = None


def _row(u: User) -> UserRow:
    return UserRow(
        id=u.id, email=u.email, role=u.role, is_active=u.is_active, access_expires=u.access_expires
    )


@router.get("/users", response_model=list[UserRow])
def list_users(session: Session = Depends(get_session)) -> list[UserRow]:
    users = session.scalars(select(User).order_by(User.id)).all()
    return [_row(u) for u in users]


@router.post("/users", response_model=UserRow, status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUser, session: Session = Depends(get_session)) -> UserRow:
    email = body.email.strip().lower()
    if body.role not in ("admin", "technician"):
        raise HTTPException(status_code=422, detail="role must be admin or technician")
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        role=body.role,
        access_expires=body.access_expires,
    )
    session.add(user)
    session.commit()
    return _row(user)


@router.patch("/users/{user_id}", response_model=UserRow)
def update_user(
    user_id: int,
    body: UpdateUser,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> UserRow:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="You can't disable your own account")
    if body.role is not None:
        if body.role not in ("admin", "technician"):
            raise HTTPException(status_code=422, detail="role must be admin or technician")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.access_expires is not None:
        user.access_expires = body.access_expires
    if body.password:
        user.password_hash = hash_password(body.password)
    session.commit()
    return _row(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account")
    session.execute(delete(User).where(User.id == user_id))
    session.commit()


# ---------------- Documents (library) ----------------
class DocumentRow(BaseModel):
    id: int
    filename: str
    chunks: int
    created_at: datetime


@router.get("/documents", response_model=list[DocumentRow])
def list_documents(session: Session = Depends(get_session)) -> list[DocumentRow]:
    rows = session.execute(
        select(Document.id, Document.filename, func.count(Chunk.id), Document.created_at)
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.filename)
    ).all()
    return [DocumentRow(id=r[0], filename=r[1], chunks=r[2], created_at=r[3]) for r in rows]


@router.post("/documents", response_model=DocumentRow, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, session: Session = Depends(get_session)) -> DocumentRow:
    """Upload a PDF and ingest it (parse -> chunk -> embed). The library's local upload path."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are supported")
    name = Path(file.filename).name  # strip any path components
    dest = Path(settings.docs_dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(await file.read())

    init_db()
    ingest_file(dest)  # embeds via Ollama; may take a moment for big PDFs

    doc = session.scalar(select(Document).where(Document.filename == name))
    if doc is None:
        raise HTTPException(status_code=500, detail="Ingestion produced no document")
    count = session.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)) or 0
    return DocumentRow(id=doc.id, filename=doc.filename, chunks=count, created_at=doc.created_at)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, session: Session = Depends(get_session)) -> None:
    doc = session.get(Document, doc_id)
    if doc is None:
        return
    file_path = Path(settings.docs_dir) / doc.filename
    session.delete(doc)  # cascades to chunks
    session.commit()
    file_path.unlink(missing_ok=True)


# ---------------- Audit ----------------
class AuditRow(BaseModel):
    user_email: str
    question: str
    source: str
    created_at: datetime


@router.get("/audit", response_model=list[AuditRow])
def list_audit(limit: int = 100, session: Session = Depends(get_session)) -> list[AuditRow]:
    rows = session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    ).all()
    return [
        AuditRow(
            user_email=r.user_email, question=r.question, source=r.source, created_at=r.created_at
        )
        for r in rows
    ]
