"""Local ingestion CLI: PDFs in a folder -> parse -> chunk -> embed -> pgvector.

Usage (from the backend venv, or `make ingest`):
    python -m app.ingestion.run <folder-with-pdfs>

Re-running is idempotent per file (existing chunks for that filename are replaced). This is
the local stand-in for the S3 -> Textract -> embed pipeline described in CLAUDE.md; locally we
read a folder instead of S3 and use pypdf (text PDFs) instead of Textract OCR.
"""

import sys
from pathlib import Path

from pypdf import PdfReader

from app.db.repository import add_chunk, upsert_document
from app.db.session import SessionLocal, init_db
from app.rag.chunking import chunk_page
from app.rag.ollama_client import embed_sync


def ingest_file(pdf_path: Path) -> int:
    """Ingest one PDF. Returns the number of chunks stored."""
    reader = PdfReader(str(pdf_path))
    session = SessionLocal()
    stored = 0
    try:
        doc = upsert_document(session, filename=pdf_path.name)
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for chunk in chunk_page(page_index, text):
                embedding = embed_sync(chunk.content)
                add_chunk(session, doc.id, chunk.page, chunk.content, embedding)
                stored += 1
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
