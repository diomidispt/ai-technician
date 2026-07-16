"""Phase-1 contract tests for the streaming chat endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_streams_tokens_then_done():
    with client.stream(
        "POST",
        "/api/chat",
        json={"messages": [{"role": "user", "content": "drum won't spin"}]},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    # SSE contract: one or more `token` events, then a terminal `done` event.
    assert "event: token" in body
    assert "event: done" in body
    # The canned reply echoes the question back.
    assert "drum" in body
