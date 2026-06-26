"""Keyword / TF-IDF-style retrieval over a document's chunks.

No external ML model and no network needed. We score each chunk against the
question using term-frequency weighted by inverse-document-frequency (IDF), then
normalise by chunk length. This behaves like a lightweight semantic search:
rarer shared words count more, common words count less.
"""
import math
import re
from collections import Counter
from typing import Dict, List

import numpy as np

from . import config, embeddings
from .models import Chunk

# Small English stopword list — enough to stop "the/of/and" dominating scores.
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "being", "with", "as", "at", "by", "from",
    "this", "that", "these", "those", "it", "its", "into", "what", "which",
    "who", "whom", "how", "when", "where", "why", "do", "does", "did", "will",
    "would", "should", "can", "could", "has", "have", "had", "you", "your",
    "i", "we", "they", "he", "she", "their", "our", "about", "please", "tell",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9$.,%/-]*")


def tokenize(text: str) -> List[str]:
    tokens = TOKEN_RE.findall(text.lower())
    cleaned = []
    for t in tokens:
        t = t.strip(".,/-")
        if t and t not in STOPWORDS and len(t) > 1:
            cleaned.append(t)
    return cleaned


def _build_idf(chunk_tokens: List[List[str]]) -> Dict[str, float]:
    n_docs = len(chunk_tokens)
    df: Counter = Counter()
    for tokens in chunk_tokens:
        for term in set(tokens):
            df[term] += 1
    # Smoothed IDF so a term in every chunk still has a small positive weight.
    return {
        term: math.log((1 + n_docs) / (1 + count)) + 1.0
        for term, count in df.items()
    }


class ScoredChunk:
    def __init__(self, chunk: Chunk, score: float):
        self.chunk = chunk
        self.score = score


def rank_chunks(question: str, chunks: List[Chunk], top_k: int) -> List[ScoredChunk]:
    """Return up to top_k chunks ranked by relevance to the question."""
    if not chunks:
        return []

    chunk_tokens = [tokenize(c.text) for c in chunks]
    idf = _build_idf(chunk_tokens)
    q_terms = set(tokenize(question))

    scored: List[ScoredChunk] = []
    for chunk, tokens in zip(chunks, chunk_tokens):
        if not tokens:
            scored.append(ScoredChunk(chunk, 0.0))
            continue
        tf = Counter(tokens)
        # Sum tf*idf over the question terms that appear in this chunk.
        raw = sum(tf[term] * idf.get(term, 0.0) for term in q_terms)
        # Normalise by sqrt(length) so long chunks don't always win.
        norm = math.sqrt(len(tokens))
        score = raw / norm if norm else 0.0
        scored.append(ScoredChunk(chunk, round(score, 4)))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:top_k]


def _rrf(rank: int, k: int) -> float:
    """Reciprocal-rank-fusion contribution for a 0-based rank position."""
    return 1.0 / (k + rank)


def hybrid_rank(
    question: str,
    chunks: List[Chunk],
    tfidf_scored: List[ScoredChunk],
    top_k: int,
) -> List[ScoredChunk]:
    """Fuse the lexical TF-IDF ranking with a dense SEMANTIC ranking via
    Reciprocal Rank Fusion, so the evidence pool also catches chunks that are
    relevant in meaning but worded differently from the question (which keyword
    TF-IDF ranks low). Each returned ScoredChunk keeps its TF-IDF score for
    display/citation; only the ORDER is fused. Falls back to the plain TF-IDF
    order when embeddings are disabled or unavailable.

    NOTE: this only decides WHICH evidence is cited / fed to the LLM. The
    abstention gate in answering.py still runs on the lexical TF-IDF scores, so
    grounding stays conservative.
    """
    qvec = embeddings.embed_query(question)
    if qvec is None:
        return tfidf_scored[:top_k]

    # Semantic ranking over every chunk that has a stored vector (one matmul).
    pairs = [(c, embeddings.to_vector(c.embedding)) for c in chunks]
    pairs = [(c, v) for c, v in pairs if v is not None and v.shape == qvec.shape]
    if not pairs:
        return tfidf_scored[:top_k]
    sims = np.vstack([v for _, v in pairs]) @ qvec  # cosine (vectors are normalized)
    sem_rank = {pairs[i][0].id: r for r, i in enumerate(np.argsort(-sims))}

    tfidf_rank = {s.chunk.id: r for r, s in enumerate(tfidf_scored)}
    # Consider the union of both candidate sets so a semantic-only hit can surface.
    by_id: Dict[int, ScoredChunk] = {s.chunk.id: s for s in tfidf_scored}
    for c, _ in pairs:
        by_id.setdefault(c.id, ScoredChunk(c, 0.0))

    k = config.HYBRID_RRF_K

    def fused_score(cid: int) -> float:
        s = 0.0
        if cid in tfidf_rank:
            s += _rrf(tfidf_rank[cid], k)
        if cid in sem_rank:
            s += _rrf(sem_rank[cid], k)
        return s

    fused = sorted(by_id.values(), key=lambda sc: fused_score(sc.chunk.id), reverse=True)
    return fused[:top_k]
