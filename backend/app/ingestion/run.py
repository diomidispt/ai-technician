"""Local ingestion CLI: PDFs in a folder -> parse -> chunk -> embed -> pgvector.

Usage (from the backend venv, or `make ingest`):
    python -m app.ingestion.run <folder-with-pdfs>

Re-running is idempotent per file (existing chunks for that filename are replaced). This is the
local stand-in for the S3 -> Textract -> embed pipeline in CLAUDE.md. Locally we read a folder
instead of S3 and use pdfplumber (text + tables) instead of Textract, with a Tesseract OCR
fallback for scanned pages/drawings (the local stand-in for Textract OCR).

Per page we emit three kinds of chunk:
  - prose  (kind="text")  — section-aware paragraph/sentence chunks
  - tables (kind="table") — each table kept whole, so parameter tables aren't shredded
  - OCR    (kind="ocr")   — for pages with little/no extractable text (scans/drawings)
"""

import logging
import sys
from pathlib import Path

import pdfplumber

from app.config import settings
from app.db.repository import add_chunk, upsert_document
from app.db.session import SessionLocal, init_db
from app.rag.chunking import chunk_page, last_heading
from app.rag.ollama_client import embed_sync

logger = logging.getLogger(__name__)


def _serialize_table(table: list[list[str | None]]) -> str:
    """Turn an extracted table into compact, searchable text (one row per line)."""
    lines = []
    for row in table:
        cells = [(c or "").strip().replace("\n", " ") for c in row]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _ocr_page(page: "pdfplumber.page.Page") -> str:
    """OCR a page image with Tesseract. Returns "" (and warns) if OCR isn't available.

    Never raises — ingestion must survive a missing `tesseract` binary or a render failure.
    """
    if not settings.ocr_enabled:
        return ""
    try:
        import pytesseract

        image = page.to_image(resolution=200).original
        return pytesseract.image_to_string(image, lang=settings.ocr_langs)
    except Exception as exc:  # tesseract missing, render failure, etc. — degrade gracefully.
        logger.warning("OCR skipped for page %s: %s", getattr(page, "page_number", "?"), exc)
        return ""


def ingest_file(pdf_path: Path) -> int:
    """Ingest one PDF. Returns the number of chunks stored."""
    session = SessionLocal()
    stored = 0
    try:
        doc = upsert_document(session, filename=pdf_path.name)
        carry_section: str | None = None  # heading in effect; headings span page boundaries
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                page_no = page.page_number
                text = page.extract_text() or ""

                # Scanned page / drawing: little extractable text -> OCR fallback.
                if len(text.strip()) < settings.ocr_min_text_chars:
                    ocr_text = _ocr_page(page)
                    if ocr_text.strip():
                        for chunk in chunk_page(page_no, ocr_text, carry_section):
                            add_chunk(
                                session,
                                doc.id,
                                page_no,
                                chunk.content,
                                embed_sync(chunk.content),
                                section=chunk.section,
                                kind="ocr",
                            )
                            stored += 1
                        carry_section = last_heading(ocr_text) or carry_section
                    continue

                # Tables kept whole, so parameter tables aren't shredded across chunks.
                for table in page.extract_tables():
                    table_text = _serialize_table(table)
                    if len(table_text.strip()) >= 20:  # skip trivial 1-cell "tables"
                        add_chunk(
                            session,
                            doc.id,
                            page_no,
                            table_text,
                            embed_sync(table_text),
                            section=carry_section,
                            kind="table",
                        )
                        stored += 1

                # Prose, section-aware.
                for chunk in chunk_page(page_no, text, carry_section):
                    add_chunk(
                        session,
                        doc.id,
                        page_no,
                        chunk.content,
                        embed_sync(chunk.content),
                        section=chunk.section,
                        kind=chunk.kind,
                    )
                    stored += 1
                carry_section = last_heading(text) or carry_section

        session.commit()
    finally:
        session.close()
    return stored


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m app.ingestion.run <folder-with-pdfs>")
        return 2

    folder = Path(argv[0])
    if not folder.is_dir():
        print(f"not a folder: {folder}")
        return 2

    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs found in {folder}")
        return 1

    init_db()
    total = 0
    for pdf in pdfs:
        print(f"ingesting {pdf.name} ...", flush=True)
        count = ingest_file(pdf)
        print(f"  -> {count} chunks", flush=True)
        total += count
    print(f"done: {len(pdfs)} file(s), {total} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
