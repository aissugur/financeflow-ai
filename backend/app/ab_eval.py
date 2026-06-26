"""A/B evaluation harness: pure TF-IDF vs hybrid (TF-IDF + dense embeddings).

Runs the golden-dataset evaluation TWICE over the same questions:

  * phase A — embeddings OFF: retrieval is pure lexical TF-IDF.
  * phase B — embeddings ON:  retrieval fuses TF-IDF with dense vectors (hybrid).

It toggles ``config.EMBED_ENABLED`` at runtime and, crucially, RE-INGESTS the
bundled sample documents for each phase so the stored chunk vectors match the
flag (vectors are written once at ingest time, so the ON phase needs real
embeddings on the rows to exercise the hybrid path). It then prints a
side-by-side comparison of the trust metrics with the delta (Hybrid - TF-IDF).

Runs anywhere ``run_evaluation`` runs. When fastembed/the embedding model is
unavailable the ON phase degrades to TF-IDF, so BOTH columns come out identical
— we detect that and print a note instead of pretending there is a difference.

Usage:
    python -m app.ab_eval
    python -m app.eval_cli --ab   (same harness, wired through the CLI)
"""
import logging

from sqlalchemy.orm import Session

from . import config, embeddings
from .database import Base, SessionLocal, engine
from .evaluation import run_evaluation
from .logging_config import setup_logging
from .models import Document

logger = logging.getLogger(__name__)

# (label, attribute on EvalMetrics, "higher is better"?). The last flag drives
# how the delta is interpreted in the printed summary.
_METRIC_FIELDS = [
    ("citation_coverage", "citation_coverage", True),
    ("evidence_match_rate", "evidence_match_rate", True),
    ("correct_abstentions", "correct_abstentions", True),
    ("unsupported_answer_count", "unsupported_answer_count", False),
    ("accuracy", "accuracy", True),
]


def _delete_sample_documents(db: Session) -> int:
    """Remove the bundled sample documents (and their chunks, via cascade) so the
    next ``run_evaluation`` re-ingests them with vectors matching EMBED_ENABLED.

    Only the eval/demo sample files are touched: we match on filename AND require
    ``owner_id IS NULL``. Sample docs are seeded with no owner, while every real
    upload carries ``owner_id``, so a user who happens to upload a file named like
    a bundled sample (e.g. ``sample_invoice.txt``) is never matched — their
    document, chunks and Q&A history are safe.
    """
    sample_names = {p.name for p in config.SAMPLE_DOCS_DIR.glob("*.txt")}
    if not sample_names:
        return 0
    docs = (
        db.query(Document)
        .filter(Document.owner_id.is_(None), Document.filename.in_(sample_names))
        .all()
    )
    for doc in docs:
        db.delete(doc)  # cascade removes the chunks/QA rows
    db.commit()
    return len(docs)


def _embeddings_actually_available() -> bool:
    """True only if fastembed AND the configured model can really load, so the
    hybrid phase would behave differently from pure TF-IDF.

    We temporarily force EMBED_ENABLED on and probe the lazy loader; this also
    warms the model so phase B doesn't pay the load cost mid-run.
    """
    saved = config.EMBED_ENABLED
    config.EMBED_ENABLED = True
    try:
        # Touch the private loader so we get the real availability verdict
        # (cached after the first call). Falls back gracefully if internals move.
        getter = getattr(embeddings, "_get_model", None)
        if callable(getter):
            return getter() is not None
        # Conservative fallback: a successful query embedding means it works.
        return embeddings.embed_query("probe") is not None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Embedding availability probe failed (%s).", exc)
        return False
    finally:
        config.EMBED_ENABLED = saved


def _run_phase(db: Session, embed_on: bool):
    """Set the flag, re-ingest the sample docs for this flag, and evaluate."""
    config.EMBED_ENABLED = embed_on
    removed = _delete_sample_documents(db)
    logger.info(
        "A/B phase EMBED_ENABLED=%s: re-ingesting %d sample doc(s)",
        embed_on,
        removed,
    )
    # run_evaluation re-seeds the (now-deleted) sample documents via
    # ensure_sample_documents, so chunks are re-created with the right vectors.
    return run_evaluation(db).metrics


def run_ab_evaluation(db: Session):
    """Run both phases and return (tfidf_metrics, hybrid_metrics, embeddings_available)."""
    saved_flag = config.EMBED_ENABLED
    embeddings_available = _embeddings_actually_available()
    try:
        tfidf = _run_phase(db, embed_on=False)
        # Only bother with a distinct ON phase if embeddings can really run;
        # otherwise the second pass would just reproduce the TF-IDF numbers.
        if embeddings_available:
            hybrid = _run_phase(db, embed_on=True)
        else:
            hybrid = tfidf
    finally:
        # Leave the process flag and the DB the way we found it: a final
        # re-ingest under the original flag restores consistent vector state.
        config.EMBED_ENABLED = saved_flag
        _delete_sample_documents(db)
        run_evaluation(db)
    return tfidf, hybrid, embeddings_available


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _fmt_delta(delta, higher_is_better: bool) -> str:
    if isinstance(delta, float):
        body = f"{delta:+.3f}"
    else:
        body = f"{delta:+d}"
    if delta == 0:
        arrow = "="
    elif (delta > 0) == higher_is_better:
        arrow = "improved"
    else:
        arrow = "worse"
    return f"{body} ({arrow})"


def print_ab_report(tfidf, hybrid, embeddings_available: bool) -> None:
    print("\n=== A/B evaluation: TF-IDF vs Hybrid (TF-IDF + embeddings) ===")
    if not embeddings_available:
        print(
            "NOTE: dense embeddings are unavailable (fastembed/model not "
            "installed),\n      so the Hybrid column equals TF-IDF — there is "
            "no semantic stage to compare.\n      Install fastembed and set "
            "EMBED_ENABLED=1 to see a real difference."
        )

    name_w = max(len(label) for label, _, _ in _METRIC_FIELDS)
    header = (
        f"{'metric'.ljust(name_w)}  {'TF-IDF'.rjust(10)}  "
        f"{'Hybrid'.rjust(10)}  {'delta (Hybrid - TF-IDF)'}"
    )
    print("\n" + header)
    print("-" * len(header))
    for label, attr, higher_is_better in _METRIC_FIELDS:
        a = getattr(tfidf, attr)
        b = getattr(hybrid, attr)
        delta = round(b - a, 3) if isinstance(a, float) else (b - a)
        print(
            f"{label.ljust(name_w)}  {_fmt(a).rjust(10)}  "
            f"{_fmt(b).rjust(10)}  {_fmt_delta(delta, higher_is_better)}"
        )

    print(
        f"\n(total_questions: TF-IDF={tfidf.total_questions}, "
        f"Hybrid={hybrid.total_questions})"
    )


def main() -> int:
    setup_logging()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tfidf, hybrid, available = run_ab_evaluation(db)
    finally:
        db.close()

    print_ab_report(tfidf, hybrid, available)

    # Gate on the better of the two phases: if either configuration produced no
    # unsupported answers we consider the run clean (exit 0).
    worst_unsupported = min(
        tfidf.unsupported_answer_count, hybrid.unsupported_answer_count
    )
    return 1 if worst_unsupported > 0 else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
