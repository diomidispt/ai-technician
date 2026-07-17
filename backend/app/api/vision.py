"""Vision input — read the text/error code off a photographed equipment display.

The technician snaps a photo (from a phone camera); this reads any codes/messages off it with a
local vision model ($0). The extracted text is returned to the UI, where it flows into the normal
manual RAG. Kept separate from /chat so the RAG flow is unchanged and the tech can review/edit the
read-back text before searching.
"""

import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import User
from app.rag import ollama_client

router = APIRouter()

_EXTRACT_PROMPT = (
    "This is a photo of an industrial laundry machine's control panel or display. "
    "Transcribe EXACTLY any error codes, alarm numbers, and on-screen messages you can read. "
    "If a specific error/alarm code is shown, put it first. Output only what is written on the "
    "display — do not guess, explain, or add anything. If no text is legible, reply: NO_TEXT_FOUND."
)

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB — plenty for a phone photo


class ExtractResponse(BaseModel):
    text: str


@router.post("/vision/extract", response_model=ExtractResponse)
async def extract(file: UploadFile, user: User = Depends(get_current_user)) -> ExtractResponse:
    if not settings.vision_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vision input is disabled"
        )
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail="Please upload an image")
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 12 MB)")

    image_b64 = base64.b64encode(data).decode()
    try:
        text = (await ollama_client.vision_extract(_EXTRACT_PROMPT, image_b64)).strip()
    except Exception as exc:  # model not pulled / Ollama error — surface a clear message.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Couldn't read the image. Is the vision model pulled "
            f"(`ollama pull {settings.vision_model}`)?",
        ) from exc

    # Some vision models wrap their answer in a ``` code fence — strip it so it doesn't pollute
    # the search query.
    if text.startswith("```"):
        text = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("```")).strip()

    if not text or "NO_TEXT_FOUND" in text.upper():
        return ExtractResponse(text="")
    return ExtractResponse(text=text)
