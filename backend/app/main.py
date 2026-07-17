"""FastAPI entrypoint for the Jensen AI Technical Support Assistant.

Local MVP: authenticated streaming RAG (`/api/chat`), local auth simulating Cognito
(`/api/auth`), and an admin console API (`/api/admin`). The model + embeddings run on Ollama
locally; the vector store is Postgres + pgvector. No AWS, $0.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.config import settings
from app.db.session import init_db, seed_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_users()
    yield


app = FastAPI(title="Jensen AI Technical Support Assistant", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(chat_router, prefix="/api")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
