"""Free web-search fallback (DuckDuckGo, no API key).

Runs ONLY when the internal library is insufficient (internal-first rule, enforced in the
pipeline). Results are clearly flagged as external. This sends the query out, so it is not
offline — set WEB_FALLBACK_ENABLED=false to disable.
"""

import asyncio
from dataclasses import dataclass

from app.config import settings

try:  # package was renamed ddgs; keep a fallback for older installs
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    from duckduckgo_search import DDGS  # type: ignore


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str


def _search_sync(query: str, count: int) -> list[WebResult]:
    out: list[WebResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=count):
            out.append(
                WebResult(
                    title=r.get("title", ""),
                    url=r.get("href") or r.get("url", ""),
                    snippet=r.get("body", ""),
                )
            )
    return out


async def search(query: str) -> list[WebResult]:
    """Return web results, or [] on any error (so the caller can fall back to a refusal)."""
    try:
        return await asyncio.to_thread(_search_sync, query, settings.web_results)
    except Exception:  # noqa: BLE001 — network/lib errors shouldn't crash the request
        return []
