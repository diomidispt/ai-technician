"""Vision input — read the text/error code off a photographed equipment display.

The technician snaps a photo (from a phone camera); this reads any codes/messages off it with a
local vision model ($0). The extracted text is returned to the UI, where it flows into the normal
manual RAG. Kept separate from /chat so the RAG flow is unchanged and the tech can review/edit the
read-back text before searching.
"""

import base64
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from PIL import Image, ImageOps
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import User
from app.rag import ollama_client

router = APIRouter()

_EXTRACT_PROMPT = (
    "You are reading a photo taken by a laundry-equipment technician, usually of a machine's "
    "control panel or digital display. Carefully transcribe any error codes, alarm numbers, and "
    "on-screen messages you can read — even if the photo is imperfect. If a specific error or "
    "alarm code is shown, put it first. Output ONLY the text visible on the display; do not "
    "guess or explain. Only if the image truly has no legible text at all, reply: NO_TEXT_FOUND."
)

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB — plenty for a phone photo
_MAX_DIM = 1568  # downscale big phone photos before sending to the model


def _prepare_image(data: bytes) -> str:
    """Normalise a phone photo for the vision model: honour EXIF rotation, downscale, re-encode.

    The EXIF step is the important one — phones store the photo unrotated with an orientation tag,
    so without it the model often sees a sideways display and can't read it.
    """
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # apply the camera's rotation tag
    img = img.convert("RGB")
    img.thumbnail((_MAX_DIM, _MAX_DIM))  # cap size, keep aspect ratio
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


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

    try:
        image_b64 = _prepare_image(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Couldn't read that image file") from exc
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
