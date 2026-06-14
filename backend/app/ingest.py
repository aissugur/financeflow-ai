"""Shared ingestion pipeline: parse -> chunk -> persist.

Used by both the upload endpoint and the evaluation endpoint so there is a
single, well-tested path for turning a file into stored chunks.
"""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from .chunking import chunk_pages
from .models import Chunk, Document
from .parsing import extract_pages

logger = logging.getLogger(__name__)


def ingest_file(db: Session, stored_path: Path, display_name: str, file_type: str) -> Document:
    """Create a Document row, extract + chunk its text, and store chunks.

    Always commits a Document row. On parse failure the document is saved with
    status='failed' and an error message instead of raising, so the dashboard
    can show the failure.
    """
    document = Document(filename=display_name, file_type=file_type, status="processed")
    db.add(document)
    db.flush()  # assign document.id without committing yet

    try:
        pages = extract_pages(stored_path, file_type)
        chunk_tuples = chunk_pages(pages)

        if not chunk_tuples:
            document.status = "failed"
            document.error = "No extractable text found in the document."
            document.num_chunks = 0
            db.commit()
            db.refresh(document)
            logger.warning("Ingest produced no chunks for %s", display_name)
            return document

        for page, index, text in chunk_tuples:
            db.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    page=page,
                    text=text,
                )
            )
        document.num_chunks = len(chunk_tuples)
        document.status = "processed"
        db.commit()
        db.refresh(document)
        logger.info(
            "Ingested '%s' (%s): %d chunks", display_name, file_type, document.num_chunks
        )
        return document

    except Exception as exc:  # keep the failed document visible in the dashboard
        document.status = "failed"
        document.error = str(exc)
        document.num_chunks = 0
        db.commit()
        db.refresh(document)
        logger.exception("Failed to ingest '%s': %s", display_name, exc)
        return document
