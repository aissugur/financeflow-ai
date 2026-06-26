"""Hybrid (TF-IDF + dense) retrieval fusion — tested offline.

We mock the query embedding so the test needs no model download. The point is to
prove the Reciprocal-Rank-Fusion logic actually lets a SEMANTIC match surface
above a chunk that scored higher on lexical TF-IDF, and that it degrades cleanly
to the TF-IDF order when embeddings are unavailable.
"""
import numpy as np

from app import embeddings
from app.models import Chunk
from app.retrieval import ScoredChunk, hybrid_rank


def _vec(*xs) -> bytes:
    return np.asarray(xs, dtype=np.float32).tobytes()


def test_rrf_surfaces_semantic_match_over_higher_tfidf(monkeypatch):
    # Query embeds to [1,0,0]. Chunk C is the semantic match; A/B are not.
    monkeypatch.setattr(embeddings, "embed_query", lambda q: np.asarray([1, 0, 0], dtype=np.float32))

    A = Chunk(id=1, document_id=1, chunk_index=0, page=1, text="alpha", embedding=_vec(0.1, 1, 0))
    B = Chunk(id=2, document_id=1, chunk_index=1, page=1, text="beta", embedding=_vec(0, 0, 1))
    C = Chunk(id=3, document_id=1, chunk_index=2, page=1, text="gamma", embedding=_vec(1, 0, 0))
    chunks = [A, B, C]

    # Lexical TF-IDF order: A best, B mid, C worst.
    tfidf = [ScoredChunk(A, 0.5), ScoredChunk(B, 0.3), ScoredChunk(C, 0.05)]

    fused = hybrid_rank("q", chunks, tfidf, top_k=3)
    order = [s.chunk.id for s in fused]

    # C (strong semantic, weak lexical) must now rank ABOVE B (weak on both),
    # even though B scored higher on TF-IDF — i.e. the dense signal moved it up.
    assert order.index(3) < order.index(2)
    # Display score is still the lexical TF-IDF score (citations stay interpretable).
    assert {s.chunk.id: s.score for s in fused}[3] == 0.05


def test_falls_back_to_tfidf_when_embeddings_unavailable(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_query", lambda q: None)
    a = Chunk(id=1, document_id=1, chunk_index=0, text="a")
    b = Chunk(id=2, document_id=1, chunk_index=1, text="b")
    tfidf = [ScoredChunk(a, 0.5), ScoredChunk(b, 0.2)]
    fused = hybrid_rank("q", [a, b], tfidf, top_k=4)
    assert [s.chunk.id for s in fused] == [1, 2]
