"""FastAPI entrypoint for the Jensen AI Technical Support Assistant.

Phase 1: serves a health check and a streaming `/api/chat` endpoint backed by a canned
reply generator (no RAG yet). The RAG core (retrieve → rerank → synthesize → citations)
will land in `app/rag/` and plug in behind the same endpoint — see CLAUDE.md.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.config import settings

app = FastAPI(title="Jensen AI Technical Support Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
