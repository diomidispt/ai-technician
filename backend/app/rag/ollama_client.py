"""Thin client for the local Ollama server (embeddings + streaming chat).

This is the one place that talks to the model provider. Swapping Ollama for Claude/Bedrock
later means adding a sibling client with the same methods — nothing else changes.

`keep_alive` is sent on every call so both the answer model and the embedding model stay
resident between requests — no multi-second reload lag on the next question.
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings


async def embed(text: str) -> list[float]:
    """Return the embedding vector for a single piece of text."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={
                "model": settings.embed_model,
                "prompt": text,
                "keep_alive": settings.ollama_keep_alive,
            },
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


def embed_sync(text: str) -> list[float]:
    """Synchronous embedding — used by the ingestion CLI."""
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embeddings",
        json={
            "model": settings.embed_model,
            "prompt": text,
            "keep_alive": settings.ollama_keep_alive,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


async def chat(messages: list[dict], model: str | None = None) -> str:
    """Single (non-streaming) completion. Used for the fast history-aware query rewrite."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model or settings.answer_model,
                "messages": messages,
                "stream": False,
                "keep_alive": settings.ollama_keep_alive,
            },
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


async def chat_stream(messages: list[dict]) -> AsyncIterator[str]:
    """Stream assistant token deltas from Ollama's /api/chat (NDJSON)."""
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.answer_model,
                "messages": messages,
                "stream": True,
                "keep_alive": settings.ollama_keep_alive,
                "options": {"num_predict": settings.answer_num_predict},
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                piece = data.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if data.get("done"):
                    break
