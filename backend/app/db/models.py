"""SQLAlchemy models.

One database holds documents + their chunked, embedded text, plus users and an audit log
(CLAUDE.md §2 Data). Users/audit are the local stand-ins for Cognito + the RDS audit tables.
"""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    """A person who can sign in. Local simulation of a Cognito user + group.

    `role` mirrors a Cognito group ("admin" | "technician"). `is_active` mirrors
    AdminDisableUser (instant revocation — checked on every request). `access_expires`
    mirrors the `custom:access_expires` contractor-expiry attribute.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="technician")  # admin | technician
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Forces a password change on next sign-in (fresh account / admin reset). Mirrors Cognito's
    # temporary-password + FORCE_CHANGE_PASSWORD flow.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    access_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLog(Base):
    """One row per answered question — the local stand-in for the RDS audit log."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str] = mapped_column(String(320), index=True)
    question: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))  # internal | web | none
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Document(Base):
    """One ingested source file (e.g. a PDF manual)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """A ~page-sized slice of a document, with its embedding for similarity search."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page: Mapped[int] = mapped_column(Integer, default=0)  # 1-based page number for citations
    # Nearest enclosing section heading (e.g. "5.2 Drum motor"), for context + richer citations.
    section: Mapped[str | None] = mapped_column(String(300), default=None)
    # How this chunk was produced: "text" (prose), "table" (kept-whole table), "ocr" (scanned page).
    kind: Mapped[str] = mapped_column(String(10), default="text")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embed_dim))

    document: Mapped["Document"] = relationship(back_populates="chunks")


# Approximate-nearest-neighbour index for fast top-k cosine search at scale (pgvector HNSW).
# Exact scan is fine for a few thousand chunks; this keeps queries fast as the library grows.
Index(
    "ix_chunks_embedding_hnsw",
    Chunk.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)

# Full-text index for the keyword half of hybrid search. `simple` config = no language-specific
# stemming, so it keeps error codes ("E14"), part numbers, and Greek words intact (Postgres has no
# Greek stemmer). Fused with the vector search via RRF (see repository.hybrid_search).
Index(
    "ix_chunks_content_fts",
    func.to_tsvector("simple", Chunk.content),
    postgresql_using="gin",
)
