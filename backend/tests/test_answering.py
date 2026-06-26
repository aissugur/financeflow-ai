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
    answer, abstained, mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is False
    assert mode == "fast"
    assert "$2,413.98" in answer  # verbatim value from the source
    assert len(citations) >= 1
    assert citations[0].document_name == "doc.txt"
    assert metadata["evidence_status"] == "supported"


def test_abstains_when_no_relevant_content():
    chunks = [make_chunk("The weather today is sunny with a light breeze.")]
    answer, abstained, _mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks
    )
    assert abstained is True
    assert answer == config.ABSTAIN_MESSAGE
    assert citations == []
    assert metadata["evidence_status"] == "abstained"
    assert metadata["cited_chunks"] == 0


def test_abstains_on_single_incidental_term_overlap():
    # The question shares only the word "number" with the source — not enough
    # evidence to answer "social security number".
    chunks = [make_chunk(INVOICE)]
    answer, abstained, _mode, citations, _metadata = answer_question(
        "What is the customer's social security number?", chunks
    )
    assert abstained is True
    assert answer == config.ABSTAIN_MESSAGE
    assert citations == []


def test_abstains_on_empty_document():
    answer, abstained, _mode, citations, metadata = answer_question("anything?", [])
    assert abstained is True
    assert citations == []
    assert metadata["evidence_status"] == "abstained"


def test_thinking_mode_falls_back_to_fast_when_llm_unavailable(monkeypatch):
    # When the LLM is unavailable (no key, or the call fails), Thinking mode must
    # transparently fall back to the Fast (extractive) engine — still grounded,
    # still cited, never broken. Patch synthesize -> None so the test is hermetic
    # regardless of any provider configured in .env.
    from app import llm

    monkeypatch.setattr(llm, "synthesize", lambda question, contexts: None)
    chunks = [make_chunk(INVOICE)]
    answer, abstained, mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks, mode="thinking"
    )
    assert abstained is False
    assert mode == "fast"  # fell back because the LLM returned nothing
    assert "$2,413.98" in answer
    assert len(citations) >= 1
    assert metadata["requested_mode"] == "thinking"
    assert metadata["answer_mode"] == "fast"


def test_thinking_mode_uses_llm_answer_when_available(monkeypatch):
    # When the LLM answers, Thinking mode returns that answer, reports
    # mode="thinking", and still attaches the grounded citations.
    from app import llm

    monkeypatch.setattr(
        llm, "synthesize", lambda q, c: "The total amount due is $2,413.98."
    )
    chunks = [make_chunk(INVOICE)]
    answer, abstained, mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks, mode="thinking"
    )
    assert abstained is False
    assert mode == "thinking"
    assert "$2,413.98" in answer
    assert len(citations) >= 1
    assert metadata["answer_mode"] == "thinking"


def test_thinking_mode_abstains_when_llm_says_so(monkeypatch):
    # If the LLM itself returns the abstain message, that must surface as an
    # abstention with no citations — never a confident-looking empty answer.
    from app import llm

    monkeypatch.setattr(llm, "synthesize", lambda q, c: config.ABSTAIN_MESSAGE)
    chunks = [make_chunk(INVOICE)]
    answer, abstained, mode, citations, metadata = answer_question(
        "What is the total amount due?", chunks, mode="thinking"
    )
    assert abstained is True
    assert mode == "thinking"
    assert citations == []
    assert metadata["evidence_status"] == "abstained"
