"""Unit tests for tokenization and TF-IDF ranking."""
from app.retrieval import rank_chunks, tokenize
from tests.conftest import make_chunk


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = tokenize("What is the TOTAL amount due?")
    assert "total" in tokens
    assert "amount" in tokens
    assert "due" in tokens
    # stopwords removed
    assert "is" not in tokens
    assert "the" not in tokens
    assert "what" not in tokens


def test_rank_chunks_orders_by_relevance():
    chunks = [
        make_chunk("The cat sat on the mat in the garden.", chunk_index=0),
        make_chunk("Total amount due is $2,413.98 on this invoice.", chunk_index=1),
        make_chunk("Payment terms are net thirty days.", chunk_index=2),
    ]
    ranked = rank_chunks("What is the total amount due?", chunks, top_k=3)
    assert ranked[0].chunk.chunk_index == 1  # the invoice-total chunk wins
    assert ranked[0].score > 0


def test_rank_chunks_empty_input():
    assert rank_chunks("anything", [], top_k=4) == []


def test_rank_chunks_respects_top_k():
    chunks = [make_chunk(f"payment number {i} due now", chunk_index=i) for i in range(6)]
    ranked = rank_chunks("payment due", chunks, top_k=2)
    assert len(ranked) == 2
