"""Unit tests that don't require Postgres or Ollama (so CI stays green).

The full end-to-end RAG flow (embed -> retrieve -> generate -> cite) is exercised manually /
via `make ingest` + the running stack, since it needs the local DB and model server.
"""

import json

from fastapi.testclient import TestClient

from app.config import settings
from app.db.repository import RetrievedChunk, _rrf_fuse, make_title
from app.main import app
from app.rag.chunking import CHUNK_OVERLAP, CHUNK_SIZE, chunk_page
from app.rag.pipeline import (
    _build_context,
    _citations,
    _detect_language,
    _parse_route,
    _recent_turns,
    _select_relevant,
    _split_history,
)

client = TestClient(app)


def _chunk(id: int, page: int, distance: float | None) -> RetrievedChunk:
    return RetrievedChunk(
        id=id, content=f"c{page}", filename="m.pdf", page=page, section=None, distance=distance
    )


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


def test_chunk_page_tracks_section_heading():
    text = "5.2 Drum motor\nCheck the drum motor wiring before replacing the belt."
    chunks = chunk_page(page=109, text=text)
    assert len(chunks) == 1
    assert chunks[0].section == "5.2 Drum motor"
    assert chunks[0].content.startswith("[Section: 5.2 Drum motor]")
    assert "drum motor wiring" in chunks[0].content


def test_chunk_page_heading_carries_across_pages():
    # A heading on page 1 stays in effect for page 2's body (headings span pages).
    from app.rag.chunking import last_heading

    page1 = "SAFETY INSTRUCTIONS\nAlways isolate power before service."
    carried = last_heading(page1)
    assert carried == "SAFETY INSTRUCTIONS"
    page2 = chunk_page(page=2, text="Wait for steam pressure to drop.", start_section=carried)
    assert page2[0].section == "SAFETY INSTRUCTIONS"


def test_citations_dedup_by_source_and_page():
    hits = [
        _chunk(1, 5, 0.1),
        _chunk(2, 5, 0.2),  # same source+page -> dedup
        _chunk(3, 6, 0.3),
    ]
    cites = _citations(hits)
    assert cites == [
        {"manual": "m.pdf", "page": 5},
        {"manual": "m.pdf", "page": 6},
    ]


def test_citations_include_section_when_present():
    hit = RetrievedChunk(
        id=1, content="x", filename="m.pdf", page=5, section="5.2 Drum motor", distance=0.1
    )
    assert _citations([hit]) == [{"manual": "m.pdf", "page": 5, "section": "5.2 Drum motor"}]


def test_select_relevant_refuses_when_best_beyond_gate():
    # Out-of-scope: every chunk is far -> nothing relevant -> refusal path.
    far = settings.sufficiency_max_distance + 0.1
    assert _select_relevant([_chunk(1, 1, far), _chunk(2, 2, far + 0.05)]) == []


def test_select_relevant_keeps_only_chunks_near_best():
    best = 0.30
    hits = [
        _chunk(1, 2, best),  # keep (best)
        _chunk(2, 4, best + settings.relevance_margin - 0.01),  # keep (within margin)
        _chunk(3, 6, best + settings.relevance_margin + 0.05),  # drop (too far from best)
    ]
    pages = [h.page for h in _select_relevant(hits)]
    assert pages == [2, 4]


def test_select_relevant_empty():
    assert _select_relevant([]) == []


def test_rrf_fuse_rewards_agreement_across_retrievers():
    # Chunk 2 is mid-rank in each list but appears in BOTH -> should win over a rank-1-in-one-list.
    vector_hits = [_chunk(1, 1, 0.10), _chunk(2, 2, 0.20), _chunk(3, 3, 0.30)]
    keyword_hits = [_chunk(4, 4, None), _chunk(2, 2, None), _chunk(5, 5, None)]
    fused = _rrf_fuse(vector_hits, keyword_hits, rrf_k=60, top_k=3)
    assert fused[0].id == 2  # present in both lists -> highest fused score
    # The vector copy (with a distance) is preserved for the sufficiency gate.
    assert fused[0].distance == 0.20


def test_rrf_fuse_respects_top_k():
    vector_hits = [_chunk(i, i, 0.1 * i) for i in range(1, 6)]
    fused = _rrf_fuse(vector_hits, [], rrf_k=60, top_k=2)
    assert len(fused) == 2


def test_parse_route():
    q = "fallback question"
    assert _parse_route('{"intent": "CHITCHAT", "query": "hello"}', q) == ("chitchat", "hello")
    assert _parse_route('{"intent": "TECHNICAL", "query": "WE110 E4"}', q) == (
        "technical",
        "WE110 E4",
    )
    # Markdown-fenced JSON (some models wrap replies in ``` ```).
    assert _parse_route('```{"intent": "CHITCHAT", "query": "hi"}```', q) == ("chitchat", "hi")
    # Missing/blank/oversized query -> fall back to the raw question.
    assert _parse_route('{"intent": "TECHNICAL"}', q) == ("technical", q)
    assert _parse_route('{"intent": "TECHNICAL", "query": "  "}', q) == ("technical", q)
    assert _parse_route(json.dumps({"intent": "TECHNICAL", "query": "x" * 301}), q) == (
        "technical",
        q,
    )
    # Unknown intent / malformed JSON / empty -> fail open to technical (never drop a real
    # question).
    assert _parse_route('{"intent": "banana", "query": "x"}', q) == ("technical", "x")
    assert _parse_route("not json", q) == ("technical", q)
    assert _parse_route("", q) == ("technical", q)


def test_make_title():
    assert make_title("  What does   E14 mean? ") == "What does E14 mean?"
    assert make_title("") == "New chat"
    assert make_title("   ") == "New chat"
    long = "word " * 40
    title = make_title(long)
    assert len(title) <= 80 and title.endswith("…")


def test_split_history_picks_last_user_message():
    history = [
        {"role": "user", "content": "What does E14 mean?"},
        {"role": "assistant", "content": "It's a drum imbalance code."},
        {"role": "user", "content": "and for the WE110?"},
    ]
    prior, question = _split_history(history)
    assert question == "and for the WE110?"
    assert prior == history[:2]  # everything before the last user turn


def test_split_history_empty():
    assert _split_history([]) == ([], "")


def test_recent_turns_caps_and_cleans():
    prior = [{"role": "user", "content": f"q{i}"} for i in range(20)]
    prior.append({"role": "system", "content": "ignored"})  # non user/assistant dropped
    turns = _recent_turns(prior)
    assert len(turns) == settings.history_max_turns
    assert all(t["role"] in ("user", "assistant") for t in turns)
    assert turns[-1]["content"] == "q19"


def test_build_context_numbers_passages():
    hits = [_chunk(1, 1, 0.1), _chunk(2, 2, 0.2)]
    ctx = _build_context(hits)
    assert "[1]" in ctx and "[2]" in ctx
    assert "page 1" in ctx and "page 2" in ctx
