"""RAG eval runner — measure retrieval + routing quality so tuning isn't guesswork.

Usage (backend venv, DB up + Ollama running, manual ingested):
    python -m app.eval.run          # or `make eval`

For each question it retrieves like the pipeline (hybrid vector+keyword, RRF-fused) and scores:
  - keyword hit  : does any top-k chunk contain an expected keyword?
  - MRR          : 1/rank of the first matching top-k chunk (retrieval precision)
  - page hit     : (if expected pages given) is one in the top-k?
  - routing      : does the sufficiency gate route internal-vs-not as expected?

Prints a per-item table + aggregates and exits non-zero below the pass thresholds (CI-ready).
Needs the live DB + Ollama, so it is intentionally NOT part of the unit test suite.
"""

import asyncio

from app.config import settings
from app.db.repository import RetrievedChunk, _rrf_fuse, keyword_search, vector_search
from app.db.session import SessionLocal, init_db
from app.eval.eval_set import EVAL_SET, EvalItem
from app.rag import ollama_client
from app.rag.pipeline import _route_and_rewrite, _select_relevant

# Pass thresholds (overall).
MIN_INTERNAL_KEYWORD_HIT = 0.60
MIN_ROUTING_ACCURACY = 0.80


def _first_match_rank(chunks: list[RetrievedChunk], keywords: list[str]) -> int | None:
    """1-based rank of the first chunk containing any keyword; None if none match."""
    lowered = [k.lower() for k in keywords]
    for rank, c in enumerate(chunks, start=1):
        text = c.content.lower()
        if any(k in text for k in lowered):
            return rank
    return None


def _evaluate(item: EvalItem) -> dict:
    # Intent routing first: chit-chat items must route to chit-chat; everything else must be
    # classified technical (and not diverted away from the manuals).
    intent, _query = asyncio.run(_route_and_rewrite([], item.question))
    if item.source == "chat":
        return {
            "keyword_hit": None,
            "mrr": 0.0,
            "page_hit": None,
            "routing_ok": intent == "chitchat",
            "predicted": intent,
            "top_pages": [],
        }

    query_embedding = ollama_client.embed_sync(item.question)
    session = SessionLocal()
    try:
        vector_hits = vector_search(session, query_embedding, settings.retrieval_candidate_k)
        keyword_hits = keyword_search(session, item.question, settings.retrieval_candidate_k)
    finally:
        session.close()

    top = _rrf_fuse(vector_hits, keyword_hits, settings.rrf_k, settings.retrieval_top_k)
    relevant = _select_relevant(vector_hits, keyword_hits)
    predicted = "internal" if relevant else "not-internal"
    expected_routing = "internal" if item.source == "internal" else "not-internal"

    rank = _first_match_rank(top, item.keywords) if item.keywords else None
    top_pages = [c.page for c in top]
    return {
        "keyword_hit": rank is not None,
        "mrr": (1.0 / rank) if rank else 0.0,
        "page_hit": (any(p in top_pages for p in item.pages) if item.pages else None),
        # A technical/web item is routed right only if it's classified technical AND the
        # retrieval gate sends it to the expected place.
        "routing_ok": intent == "technical" and predicted == expected_routing,
        "predicted": predicted if intent == "technical" else "chitchat",
        "top_pages": top_pages,
    }


def main() -> int:
    init_db()
    print(
        f"Eval: {len(EVAL_SET)} questions | model={settings.answer_model} "
        f"embed={settings.embed_model} hybrid={settings.hybrid_enabled}\n"
    )
    header = f"{'src':<12} {'kw':<4} {'mrr':<5} {'route':<6} {'pages':<16} question"
    print(header)
    print("-" * len(header))

    internal_kw_hits, internal_n = 0, 0
    routing_ok, mrr_sum = 0, 0.0
    for item in EVAL_SET:
        r = _evaluate(item)
        routing_ok += int(r["routing_ok"])
        mrr_sum += r["mrr"]
        if item.source == "internal":
            internal_n += 1
            internal_kw_hits += int(r["keyword_hit"])
        kw = "—" if r["keyword_hit"] is None else ("✓" if r["keyword_hit"] else "·")
        route = "✓" if r["routing_ok"] else "✗"
        pages = ",".join(str(p) for p in r["top_pages"][:5])
        print(
            f"{item.source:<12} {kw:<4} {r['mrr']:<5.2f} {route:<6} {pages:<16} "
            f"{item.question[:48]}"
        )

    n = len(EVAL_SET)
    kw_rate = internal_kw_hits / internal_n if internal_n else 0.0
    route_acc = routing_ok / n if n else 0.0
    mean_mrr = mrr_sum / n if n else 0.0
    print("\nAggregate:")
    print(f"  internal keyword hit-rate : {kw_rate:.2f}  (>= {MIN_INTERNAL_KEYWORD_HIT} to pass)")
    print(f"  routing accuracy          : {route_acc:.2f}  (>= {MIN_ROUTING_ACCURACY} to pass)")
    print(f"  mean MRR (all)            : {mean_mrr:.2f}")

    passed = kw_rate >= MIN_INTERNAL_KEYWORD_HIT and route_acc >= MIN_ROUTING_ACCURACY
    print(f"\n{'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
