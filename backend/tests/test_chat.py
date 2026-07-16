"""Unit tests that don't require Postgres or Ollama (so CI stays green).

The full end-to-end RAG flow (embed -> retrieve -> generate -> cite) is exercised manually /
via `make ingest` + the running stack, since it needs the local DB and model server.
"""

from fastapi.testclient import TestClient

from app.config import settings
from app.db.repository import RetrievedChunk
from app.main import app
from app.rag.chunking import CHUNK_OVERLAP, CHUNK_SIZE, chunk_page
from app.rag.pipeline import _build_context, _citations, _detect_language, _select_relevant

client = TestClient(app)


def test_detect_language():
    assert _detect_language("How do I service the steam valve?") == "English"
    assert _detect_language("What does E14 mean?") == "English"
    assert _detect_language("Ο κάδος δεν γυρίζει, τι να ελέγξω;") == "Greek"
    # Mixed (Greek question referencing an English code) still detects Greek.
    assert _detect_language("Τι σημαίνει ο κωδικός E14;") == "Greek"


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chunk_page_splits_long_text_with_overlap():
    text = "word " * 2000  # ~10k chars, well over one chunk
    chunks = chunk_page(page=3, text=text)
    assert len(chunks) > 1
    assert all(c.page == 3 for c in chunks)
    assert all(len(c.content) <= CHUNK_SIZE for c in chunks)
    # consecutive chunks overlap
    assert chunks[0].content[-CHUNK_OVERLAP:] in chunks[0].content


def test_chunk_page_empty():
    assert chunk_page(1, "   ") == []


def test_citations_dedup_by_source_and_page():
    hits = [
        RetrievedChunk("a", "manual.pdf", 5, 0.1),
        RetrievedChunk("b", "manual.pdf", 5, 0.2),  # same source+page -> dedup
        RetrievedChunk("c", "manual.pdf", 6, 0.3),
    ]
    cites = _citations(hits)
    assert cites == [
        {"manual": "manual.pdf", "page": 5},
        {"manual": "manual.pdf", "page": 6},
    ]


def _hit(page: int, distance: float) -> RetrievedChunk:
    return RetrievedChunk(content=f"c{page}", filename="m.pdf", page=page, distance=distance)


def test_select_relevant_refuses_when_best_beyond_gate():
    # Out-of-scope: every chunk is far -> nothing relevant -> refusal path.
    far = settings.sufficiency_max_distance + 0.1
    assert _select_relevant([_hit(1, far), _hit(2, far + 0.05)]) == []


def test_select_relevant_keeps_only_chunks_near_best():
    best = 0.30
    hits = [
        _hit(2, best),                                   # keep (best)
        _hit(4, best + settings.relevance_margin - 0.01),  # keep (within margin)
        _hit(6, best + settings.relevance_margin + 0.05),  # drop (too far from best)
    ]
    pages = [h.page for h in _select_relevant(hits)]
    assert pages == [2, 4]


def test_select_relevant_empty():
    assert _select_relevant([]) == []


def test_build_context_numbers_passages():
    hits = [
        RetrievedChunk("first", "m.pdf", 1, 0.1),
        RetrievedChunk("second", "m.pdf", 2, 0.2),
    ]
    ctx = _build_context(hits)
    assert "[1]" in ctx and "[2]" in ctx
    assert "page 1" in ctx and "page 2" in ctx
