"""Data access for documents and chunks. All vector/keyword SQL lives here — never in handlers."""

from sqlalchemy import delete, func, select
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


def add_chunk(
    session: Session,
    document_id: int,
    page: int,
    content: str,
    embedding: list[float],
    *,
    section: str | None = None,
    kind: str = "text",
) -> None:
    session.add(
        Chunk(
            document_id=document_id,
            page=page,
            content=content,
            embedding=embedding,
            section=section,
            kind=kind,
        )
    )


class RetrievedChunk:
    """A search hit plus its source, ready to cite.

    `distance` is the vector cosine distance (lower = more similar) when this chunk was found by
    the vector retriever; None for keyword-only hits. The internal-first sufficiency gate uses it.
    """

    def __init__(
        self,
        id: int,
        content: str,
        filename: str,
        page: int,
        section: str | None,
        distance: float | None,
    ):
        self.id = id
        self.content = content
        self.filename = filename
        self.page = page
        self.section = section
        self.distance = distance


def vector_search(
    session: Session, query_embedding: list[float], top_k: int
) -> list[RetrievedChunk]:
    """Top-k nearest chunks by cosine distance (pgvector `<=>`). Lower distance = more similar."""
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    rows = session.execute(
        select(Chunk.id, Chunk.content, Document.filename, Chunk.page, Chunk.section, distance)
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k)
    ).all()
    return [
        RetrievedChunk(id=r[0], content=r[1], filename=r[2], page=r[3], section=r[4], distance=r[5])
        for r in rows
    ]


# Backwards-compatible alias (older callers / tests).
search_chunks = vector_search


def keyword_search(session: Session, query_text: str, top_k: int) -> list[RetrievedChunk]:
    """Top-k chunks by Postgres full-text relevance (`ts_rank`). Catches exact tokens vectors blur.

    Uses the `simple` config (no stemming) to keep codes/part numbers/Greek intact, matching the
    GIN index in models.py. Returns chunks with `distance=None` (keyword hits carry no vector).
    """
    tsvector = func.to_tsvector("simple", Chunk.content)
    tsquery = func.plainto_tsquery("simple", query_text)
    rank = func.ts_rank(tsvector, tsquery).label("rank")
    rows = session.execute(
        select(Chunk.id, Chunk.content, Document.filename, Chunk.page, Chunk.section)
        .join(Document, Document.id == Chunk.document_id)
        .where(tsvector.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(top_k)
    ).all()
    return [
        RetrievedChunk(id=r[0], content=r[1], filename=r[2], page=r[3], section=r[4], distance=None)
        for r in rows
    ]


def _rrf_fuse(
    vector_hits: list[RetrievedChunk],
    keyword_hits: list[RetrievedChunk],
    rrf_k: int,
    top_k: int,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion of two ranked lists.

    Each list is assumed ordered best-first. A chunk's fused score is the sum over the lists it
    appears in of 1 / (rrf_k + rank), rank being 1-based. Chunks ranked well by BOTH retrievers
    rise to the top — a lightweight reranker with no model. Vector distance is preserved from the
    vector hit (kept for the sufficiency gate); ties break on best (lowest) rank seen.
    """
    scores: dict[int, float] = {}
    best_rank: dict[int, int] = {}
    merged: dict[int, RetrievedChunk] = {}

    for hits in (vector_hits, keyword_hits):
        for rank, hit in enumerate(hits, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (rrf_k + rank)
            best_rank[hit.id] = min(best_rank.get(hit.id, rank), rank)
            existing = merged.get(hit.id)
            if existing is None:
                merged[hit.id] = hit
            elif existing.distance is None and hit.distance is not None:
                # Prefer the copy that carries a vector distance (for the sufficiency gate).
                merged[hit.id] = hit

    ordered = sorted(merged.values(), key=lambda c: (-scores[c.id], best_rank[c.id], c.id))
    return ordered[:top_k]


def hybrid_search(
    session: Session,
    query_embedding: list[float],
    query_text: str,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
) -> list[RetrievedChunk]:
    """Vector + keyword retrieval fused via RRF. Returns the top_k fused chunks."""
    vector_hits = vector_search(session, query_embedding, candidate_k)
    keyword_hits = keyword_search(session, query_text, candidate_k)
    return _rrf_fuse(vector_hits, keyword_hits, rrf_k, top_k)
