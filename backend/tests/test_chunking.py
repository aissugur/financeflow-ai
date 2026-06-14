"""Unit tests for the chunking logic."""
from app.chunking import CHUNK_SIZE_WORDS, chunk_pages


def test_short_text_makes_one_chunk():
    chunks = chunk_pages([(None, "Invoice total is 100 dollars.")])
    assert len(chunks) == 1
    page, index, text = chunks[0]
    assert index == 0
    assert "Invoice" in text


def test_long_text_splits_with_sequential_indices():
    words = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_pages([(1, words)])
    assert len(chunks) > 1
    # indices are contiguous starting at 0
    assert [c[1] for c in chunks] == list(range(len(chunks)))
    # page number is carried through
    assert all(c[0] == 1 for c in chunks)


def test_chunks_overlap():
    words = " ".join(f"w{i}" for i in range(CHUNK_SIZE_WORDS * 2))
    chunks = chunk_pages([(None, words)])
    first_words = set(chunks[0][2].split())
    second_words = set(chunks[1][2].split())
    assert first_words & second_words, "adjacent chunks should overlap"


def test_empty_pages_yield_no_chunks():
    assert chunk_pages([(None, "   "), (2, "")]) == []
