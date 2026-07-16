"""Data access for documents and chunks. All vector SQL lives here — never in route handlers."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document


def upsert_document(session: Session, filename: str, title: str = "") -> Document:
    """Get-or-create a document, clearing any existing chunks so re-ingest is idempotent."""
    doc = session.scalar(select(Document).where(Document.filename == filename))
    if doc is None:
        doc = Document(filename=filename, title=title or filename)
        session.add(doc)
        session.flush()
    else:
        session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    return doc


def add_chunk(session: Session, document_id: int, page: int, content: str, embedding: list[float]):
    session.add(Chunk(document_id=document_id, page=page, content=content, embedding=embedding))


class RetrievedChunk:
    """A search hit plus its source, ready to cite."""

    def __init__(self, content: str, filename: str, page: int, distance: float):
        self.content = content
        self.filename = filename
        self.page = page
        self.distance = distance


def search_chunks(
    session: Session, query_embedding: list[float], top_k: int
) -> list[RetrievedChunk]:
    """Top-k nearest chunks by cosine distance (pgvector `<=>`). Lower distance = more similar."""
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    rows = session.execute(
        select(Chunk.content, Document.filename, Chunk.page, distance)
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k)
    ).all()
    return [RetrievedChunk(content=r[0], filename=r[1], page=r[2], distance=r[3]) for r in rows]
