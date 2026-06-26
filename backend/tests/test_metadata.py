"""Focused unit tests for the answer metadata dict (the shared-contract 5th
element of answer_question). These assert the metadata's shape, the confidence
range/calibration, evidence_status, and chunk counts — independently of the
answer text itself."""
from app import config
from app.answering import answer_question
from tests.conftest import make_chunk

INVOICE = (
    "Invoice Number INV-2025-0473. Invoice Date March 3 2025. Due Date April 2 "
    "2025. Subtotal $2,230.00. Tax $183.98. Total Amount Due $2,413.98. "
    "Payment terms net 30."
)

# Every metadata dict must carry exactly these keys (shared contract).
EXPECTED_KEYS = {
    "question_type",
    "evidence_status",
    "confidence",
    "top_score",
    "matched_terms",
    "required_terms",
    "retrieved_chunks",
    "cited_chunks",
    "requested_mode",
    "answer_mode",
    "latency_ms",
}


def test_metadata_supported_answer_shape_and_confidence():
    chunks = [make_chunk(INVOICE)]
    _answer, abstained, _mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is False
    # Contract: the full key set is always present.
    assert set(metadata) == EXPECTED_KEYS
    assert metadata["evidence_status"] == "supported"
    # Confidence is a 0..1 float; a solid invoice-total match should be high.
    assert 0.0 <= metadata["confidence"] <= 1.0
    assert metadata["confidence"] >= 0.6
    # cited_chunks mirrors the returned citations.
    assert metadata["cited_chunks"] == len(citations)
    assert metadata["cited_chunks"] >= 1
    assert metadata["question_type"] == "invoice_total"
    assert metadata["latency_ms"] >= 0
    assert isinstance(metadata["latency_ms"], int)


def test_metadata_abstained_low_confidence_and_no_citations():
    chunks = [make_chunk("The weather today is sunny with a light breeze.")]
    _answer, abstained, _mode, _citations, metadata = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is True
    assert set(metadata) == EXPECTED_KEYS
    assert metadata["evidence_status"] == "abstained"
    assert metadata["confidence"] == 0.0
    assert metadata["cited_chunks"] == 0


def test_metadata_confidence_in_unit_range_for_empty_document():
    _answer, abstained, _mode, _citations, metadata = answer_question("anything?", [])
    assert abstained is True
    assert 0.0 <= metadata["confidence"] <= 1.0
    assert metadata["evidence_status"] == "abstained"
    assert metadata["retrieved_chunks"] == 0


def test_metadata_question_type_payment_terms():
    chunks = [make_chunk(INVOICE)]
    _answer, _abstained, _mode, _citations, metadata = answer_question(
        "What are the payment terms?", chunks
    )
    assert metadata["question_type"] == "payment_terms"


def test_metadata_match_text_populated_on_citation():
    chunks = [make_chunk(INVOICE)]
    _answer, _abstained, _mode, citations, _metadata = answer_question(
        "What is the total amount due?", chunks
    )
    assert citations
    # The focused span the question matched is surfaced for UI highlighting and
    # is a verbatim substring of the chunk text.
    assert citations[0].match_text is not None
    assert citations[0].match_text in INVOICE
