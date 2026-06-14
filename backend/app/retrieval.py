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
