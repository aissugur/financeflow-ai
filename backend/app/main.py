"""FastAPI application: all HTTP endpoints for FinanceFlow AI."""
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import Request

from . import config
from .answering import answer_question
from .database import Base, engine, get_db
from .evaluation import ensure_sample_documents, run_evaluation
from .ingest import ingest_file
from .logging_config import setup_logging
from .models import QA, Chunk, Document
from .schemas import (
    AskRequest,
    AskResponse,
    Citation,
    DemoSeedResponse,
    DocumentDeleted,
    DocumentOut,
    EvalResponse,
    QAOut,
)

setup_logging()
logger = logging.getLogger(__name__)

# Create tables on startup (simple for an MVP; use migrations for production).
Base.metadata.create_all(bind=engine)

TAGS_METADATA = [
    {"name": "Health", "description": "Service status and current answer mode."},
    {"name": "Documents", "description": "Upload, list, inspect, and delete documents."},
    {"name": "Q&A", "description": "Ask grounded questions and review past answers."},
    {"name": "Evaluation", "description": "Anti-hallucination golden-dataset evaluation."},
    {"name": "Demo", "description": "One-click seeding so the app is testable instantly."},
]

app = FastAPI(
    title="FinanceFlow AI",
    version="1.0.0",
    description=(
        "Retrieval-Augmented Q&A over business finance documents. Every answer is "
        "grounded in retrieved evidence with citations, and the service **abstains** "
        "instead of guessing when the document doesn't support an answer."
    ),
    openapi_tags=TAGS_METADATA,
)

# Allow any local-dev origin (any port on localhost / 127.0.0.1) so the app
# works whether the frontend runs on 5173, a different Vite port, or in Docker.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last line of defence: log the stack trace and return a clean 500 instead
    of leaking a traceback. The app should never crash a request."""
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["Health"], summary="Health check")
def health():
    """Return service status and the active answer mode (extractive or llm)."""
    return {
        "status": "ok",
        "answer_mode": config.ANSWER_MODE,
        "llm_provider": config.LLM_PROVIDER if config.ANSWER_MODE == "llm" else None,
    }


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
@app.post(
    "/documents/upload",
    response_model=DocumentOut,
    tags=["Documents"],
    summary="Upload a PDF or TXT document",
    description=(
        "Validates the file type (PDF/TXT) and size (max 10 MB), extracts text, "
        "splits it into overlapping chunks, and stores the chunks. The raw file is "
        "parsed in a temp location and then discarded — only extracted text is kept."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="A PDF or TXT file, up to 10 MB."),
    db: Session = Depends(get_db),
):
    original_name = (file.filename or "").strip()
    if not original_name:
        raise HTTPException(status_code=400, detail="Missing filename.")

    ext = Path(original_name).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Allowed types: PDF, TXT.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        mb = config.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large (max {mb} MB).")

    logger.info("Upload received: %s (%d bytes)", original_name, len(raw))

    # Parse from a temp file, then discard it (removed even on failure).
    file_type = "pdf" if ext == ".pdf" else "txt"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(raw)
        tmp.close()
        document = ingest_file(db, Path(tmp.name), original_name, file_type)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return document


@app.get(
    "/documents",
    response_model=List[DocumentOut],
    tags=["Documents"],
    summary="List all documents",
)
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@app.get(
    "/documents/{document_id}",
    response_model=DocumentOut,
    tags=["Documents"],
    summary="Get one document's metadata",
)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@app.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleted,
    tags=["Documents"],
    summary="Delete a document",
    description="Deletes the document and cascades to its chunks and Q&A history.",
)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    db.delete(document)  # cascades to chunks + qa history
    db.commit()
    logger.info("Deleted document %d (%s)", document_id, document.filename)
    return DocumentDeleted(deleted=document_id)


# --------------------------------------------------------------------------- #
# Q&A
# --------------------------------------------------------------------------- #
@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["Q&A"],
    summary="Ask a question about a document",
    description=(
        "Retrieves the most relevant chunks and answers **only** from them. "
        "Returns citations (document, page/chunk, excerpt, score). If the evidence "
        "is too weak, the answer is exactly: "
        "'Not enough information in the uploaded document.'"
    ),
)
def ask(req: AskRequest, db: Session = Depends(get_db)):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    document = db.get(Document, req.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.status != "processed":
        raise HTTPException(
            status_code=400,
            detail="Document was not processed successfully and cannot be queried.",
        )

    chunks = db.query(Chunk).filter(Chunk.document_id == document.id).all()
    answer, abstained, mode, citations = answer_question(question, chunks, req.mode)
    logger.info(
        "Ask doc=%d abstained=%s citations=%d q=%r",
        document.id,
        abstained,
        len(citations),
        question[:80],
    )

    db.add(
        QA(
            document_id=document.id,
            question=question,
            answer=answer,
            abstained=1 if abstained else 0,
            citations_json=json.dumps([c.model_dump() for c in citations]),
        )
    )
    db.commit()

    return AskResponse(answer=answer, abstained=abstained, mode=mode, citations=citations)


@app.get(
    "/history",
    response_model=List[QAOut],
    tags=["Q&A"],
    summary="List past questions and answers",
)
def history(document_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(QA).order_by(QA.created_at.desc())
    if document_id is not None:
        query = query.filter(QA.document_id == document_id)
    rows = query.limit(100).all()

    result: List[QAOut] = []
    for r in rows:
        raw = json.loads(r.citations_json or "[]")
        result.append(
            QAOut(
                id=r.id,
                document_id=r.document_id,
                question=r.question,
                answer=r.answer,
                abstained=bool(r.abstained),
                citations=[Citation(**c) for c in raw],
                created_at=r.created_at,
            )
        )
    return result


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@app.post(
    "/evaluate",
    response_model=EvalResponse,
    tags=["Evaluation"],
    summary="Run the golden-dataset evaluation",
    description=(
        "Runs the bundled golden questions against the sample documents and reports "
        "answered-with-citation, correct-abstention, unsupported-answer, citation "
        "coverage, and evidence-match metrics."
    ),
)
def evaluate(db: Session = Depends(get_db)):
    return run_evaluation(db)


# --------------------------------------------------------------------------- #
# Demo
# --------------------------------------------------------------------------- #
@app.post(
    "/demo/seed",
    response_model=DemoSeedResponse,
    tags=["Demo"],
    summary="Load the bundled sample documents",
    description="Ingests the sample invoice, contract, and payment note (idempotent) "
    "so a reviewer can try the app in seconds.",
)
def seed_demo(db: Session = Depends(get_db)):
    docs = ensure_sample_documents(db)
    seeded = sorted(docs.values(), key=lambda d: d.filename)
    logger.info("Demo seed requested: %d sample documents available", len(seeded))
    return DemoSeedResponse(
        seeded=seeded,
        message=f"Loaded {len(seeded)} sample documents. Head to the Ask tab to try them.",
    )
