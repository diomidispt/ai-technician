"""Split document text into embed-sized chunks, preserving page numbers for citations."""

from dataclasses import dataclass

# ~1000 tokens ≈ 4000 chars; keep some overlap so answers spanning a boundary still retrieve.
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


@dataclass
class TextChunk:
    page: int
    content: str


def chunk_page(page: int, text: str) -> list[TextChunk]:
    """Chunk a single page's text with character overlap."""
    text = " ".join(text.split())  # normalise whitespace
    if not text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP
    while start < len(text):
        piece = text[start : start + CHUNK_SIZE]
        chunks.append(TextChunk(page=page, content=piece))
        start += step
    return chunks
