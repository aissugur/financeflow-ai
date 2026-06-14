"""Unit tests for the answer + abstention logic (the anti-hallucination core)."""
from app import config
from app.answering import answer_question
from tests.conftest import make_chunk

INVOICE = (
    "Invoice Number INV-2025-0473. Invoice Date March 3 2025. Due Date April 2 "
    "2025. Subtotal $2,230.00. Tax $183.98. Total Amount Due $2,413.98. "
    "Payment terms net 30."
)


def test_answerable_question_returns_grounded_answer_with_citation():
    chunks = [make_chunk(INVOICE)]
    answer, abstained, mode, citations = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is False
    assert mode == "extractive"
    assert "$2,413.98" in answer  # verbatim value from the source
    assert len(citations) >= 1
    assert citations[0].document_name == "doc.txt"


def test_abstains_when_no_relevant_content():
    chunks = [make_chunk("The weather today is sunny with a light breeze.")]
    answer, abstained, _mode, citations = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is True
    assert answer == config.ABSTAIN_MESSAGE
    assert citations == []


def test_abstains_on_single_incidental_term_overlap():
    # The question shares only the word "number" with the source — not enough
    # evidence to answer "social security number".
    chunks = [make_chunk(INVOICE)]
    answer, abstained, _mode, citations = answer_question(
        "What is the customer's social security number?", chunks
    )
    assert abstained is True
    assert answer == config.ABSTAIN_MESSAGE
    assert citations == []


def test_abstains_on_empty_document():
    answer, abstained, _mode, citations = answer_question("anything?", [])
    assert abstained is True
    assert citations == []
