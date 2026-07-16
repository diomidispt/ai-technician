"""Split document text into embed-sized chunks, preserving page numbers for citations.

Strategy: respect natural boundaries. Split a page into paragraphs, then pack whole paragraphs
(or sentences, for long ones) into chunks up to a target size, carrying a short overlap so an
answer that straddles a boundary is still retrievable. This beats blind fixed-width cuts, which
slice mid-sentence and hurt both retrieval and citation quality.
"""

import re
from dataclasses import dataclass

CHUNK_SIZE = 1000  # target max characters per chunk (~250-300 tokens)
CHUNK_OVERLAP = 150  # characters of continuity carried between adjacent chunks

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n+")


@dataclass
class TextChunk:
    page: int
    content: str


def _hard_split(text: str) -> list[str]:
    """Last resort: split an over-long unit on character windows with overlap."""
    step = CHUNK_SIZE - CHUNK_OVERLAP
    return [text[i : i + CHUNK_SIZE] for i in range(0, len(text), step)]


def _atomize(paragraph: str) -> list[str]:
    """Break a paragraph into units no larger than CHUNK_SIZE (by sentence, then by force)."""
    if len(paragraph) <= CHUNK_SIZE:
        return [paragraph]
    units: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(paragraph):
        sentence = sentence.strip()
        if not sentence:
            continue
        units.extend([sentence] if len(sentence) <= CHUNK_SIZE else _hard_split(sentence))
    return units


def _pack(units: list[str]) -> list[str]:
    """Greedily pack units into chunks, overlapping by the trailing unit when it's short."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for unit in units:
        addition = len(unit) + (1 if current else 0)
        if current and length + addition > CHUNK_SIZE:
            chunks.append(" ".join(current))
            if len(current[-1]) < CHUNK_OVERLAP:  # carry a short tail for continuity
                current = [current[-1], unit]
                length = len(current[-1]) + 1 + len(unit)
            else:
                current = [unit]
                length = len(unit)
        else:
            current.append(unit)
            length += addition
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_page(page: int, text: str) -> list[TextChunk]:
    """Chunk a single page's text on paragraph/sentence boundaries."""
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(_atomize(" ".join(paragraph.split())))
    return [TextChunk(page=page, content=c) for c in _pack(units)]
