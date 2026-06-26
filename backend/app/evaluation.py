"""Anti-hallucination evaluation harness.

Loads a small *golden dataset* (questions paired with the document they target,
whether they should be answerable, and the evidence we expect to be cited), runs
each question through the real answer pipeline, and reports trust-focused
metrics:

  * total_questions
  * answered_with_citation
  * correct_abstentions
  * unsupported_answer_count
  * citation_coverage      (cited answers / answerable questions)
  * evidence_match_rate    (expected evidence found / answerable questions)

The same harness powers both the `/evaluate` API and the `eval_cli` command.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import Session

from . import config
from .answering import answer_question
from .ingest import ingest_file
from .models import Chunk, Document
from .schemas import Citation, EvalCase, EvalMetrics, EvalResponse

logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"


def load_golden_dataset() -> List[dict]:
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def ensure_sample_documents(db: Session) -> Dict[str, Document]:
    """Ingest each bundled sample document once (idempotent). Returns name->doc."""
    by_name: Dict[str, Document] = {}
    for path in sorted(config.SAMPLE_DOCS_DIR.glob("*.txt")):
        existing = (
            db.query(Document)
            .filter(Document.filename == path.name, Document.status == "processed")
            .first()
        )
        if existing:
            by_name[path.name] = existing
            continue
        logger.info("Seeding sample document: %s", path.name)
        by_name[path.name] = ingest_file(db, path, path.name, "txt")
    return by_name


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def _evidence_in_output(expected: str, answer: str, citations: List[Citation]) -> bool:
    """True if the expected evidence string appears in the answer or any cited
    excerpt (whitespace-insensitive, case-insensitive)."""
    needle = _normalize(expected)
    haystacks = [answer] + [c.excerpt for c in citations]
    return any(needle in _normalize(h) for h in haystacks)


def run_evaluation(db: Session) -> EvalResponse:
    dataset = load_golden_dataset()
    docs = ensure_sample_documents(db)
    logger.info("Running evaluation over %d golden questions", len(dataset))

    cases: List[EvalCase] = []
    answered_with_citation = 0
    correct_abstentions = 0
    unsupported_answer_count = 0
    evidence_matches = 0
    answerable_total = 0

    for item in dataset:
        doc = docs.get(item["document"])
        if doc is None:
            logger.warning("Golden item references missing document: %s", item["document"])
            continue

        chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        answer, abstained, _mode, citations, _metadata = answer_question(
            item["question"], chunks
        )
        has_citation = len(citations) > 0
        expectation = item["expectation"]
        expected_evidence = item.get("expected_evidence")
        evidence_found = False

        if expectation == "answerable":
            answerable_total += 1
            passed = (not abstained) and has_citation
            if passed:
                answered_with_citation += 1
            if (not abstained) and not has_citation:
                unsupported_answer_count += 1
            if expected_evidence and _evidence_in_output(
                expected_evidence, answer, citations
            ):
                evidence_found = True
                evidence_matches += 1
        else:  # should_abstain
            passed = abstained
            if abstained:
                correct_abstentions += 1
            else:
                unsupported_answer_count += 1

        cases.append(
            EvalCase(
                question=item["question"],
                document=item["document"],
                expectation=expectation,
                expected_evidence=expected_evidence,
                answer=answer,
                abstained=abstained,
                has_citation=has_citation,
                evidence_found=evidence_found,
                passed=passed,
                citations=[
                    c if isinstance(c, Citation) else Citation(**c) for c in citations
                ],
            )
        )

    total = len(cases)
    passed_total = sum(1 for c in cases if c.passed)
    metrics = EvalMetrics(
        total_questions=total,
        answered_with_citation=answered_with_citation,
        correct_abstentions=correct_abstentions,
        unsupported_answer_count=unsupported_answer_count,
        citation_coverage=round(answered_with_citation / answerable_total, 3)
        if answerable_total
        else 0.0,
        evidence_match_rate=round(evidence_matches / answerable_total, 3)
        if answerable_total
        else 0.0,
        passed=passed_total,
        accuracy=round(passed_total / total, 3) if total else 0.0,
    )
    logger.info(
        "Evaluation done: %d/%d passed, %d unsupported answers",
        passed_total,
        total,
        unsupported_answer_count,
    )
    return EvalResponse(cases=cases, metrics=metrics)
