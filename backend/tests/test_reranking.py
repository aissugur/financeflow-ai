"""Unit tests for the optional second-stage reranker (reranking.py).

These cover the graceful-fallback contract (the app must never break when the
reranker is disabled or unavailable) and that a working ranker actually reorders.
"""
import pytest

from app import config, reranking
from app.retrieval import ScoredChunk
from tests.conftest import make_chunk

try:
    import flashrank  # noqa: F401

    HAS_FLASHRANK = True
except Exception:
    HAS_FLASHRANK = False


def _scored():
    # TF-IDF order: alpha(0) > bravo(1) > charlie(2)
    return [
        ScoredChunk(make_chunk("alpha", chunk_index=0), 0.9),
        ScoredChunk(make_chunk("bravo", chunk_index=1), 0.5),
        ScoredChunk(make_chunk("charlie", chunk_index=2), 0.1),
    ]


def test_rerank_disabled_keeps_tfidf_order(monkeypatch):
    monkeypatch.setattr(config, "RERANK_ENABLED", False)
    out = reranking.rerank("anything", _scored(), top_k=2)
    assert [s.chunk.chunk_index for s in out] == [0, 1]  # untouched TF-IDF order, trimmed


def test_rerank_unavailable_falls_back_to_tfidf(monkeypatch):
    # Enabled, but the ranker can't be built -> must fall back to TF-IDF order.
    monkeypatch.setattr(config, "RERANK_ENABLED", True)
    monkeypatch.setattr(reranking, "_get_ranker", lambda: None)
    out = reranking.rerank("anything", _scored(), top_k=2)
    assert [s.chunk.chunk_index for s in out] == [0, 1]


@pytest.mark.skipif(not HAS_FLASHRANK, reason="flashrank not installed")
def test_rerank_reorders_with_a_working_ranker(monkeypatch):
    # A fake ranker that promotes charlie(2) to the top proves we honour its order.
    monkeypatch.setattr(config, "RERANK_ENABLED", True)

    class FakeRanker:
        def rerank(self, _req):
            return [{"id": 2}, {"id": 0}, {"id": 1}]

    monkeypatch.setattr(reranking, "_get_ranker", lambda: FakeRanker())
    out = reranking.rerank("anything", _scored(), top_k=2)
    assert [s.chunk.chunk_index for s in out] == [2, 0]
