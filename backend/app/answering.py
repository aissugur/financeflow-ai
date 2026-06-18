"""Turn retrieved chunks into a grounded, citation-backed answer.

Two modes:
  * extractive (default): return the most relevant verbatim span from the top
    chunks. No model, no hallucination risk — every word comes from the document.
  * llm (optional): synthesize a short answer from the same context, with a
    strict prompt that forbids inventing facts and requires abstention.

Either way we abstain when retrieval is too weak, and we always return the
evidence (citations) so the user can verify.
"""
import logging
from typing import List, Optional, Set, Tuple

from . import config, llm
from .models import Chunk
from .retrieval import ScoredChunk, rank_chunks, tokenize
from .schemas import Citation

logger = logging.getLogger(__name__)


def _excerpt(text: str, limit: int = 320) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _focused_span(
    q_terms: Set[str], text: str, window_words: int
) -> Optional[Tuple[int, str]]:
    """Return (match_count, snippet) for the densest window of question terms.

    Sentence splitting is unreliable on finance docs (invoices/tables have few
    periods), so we slide a fixed word window and keep the region with the most
    matches, re-centered on the matched terms so the value next to a label like
    "Total Amount Due  $2,413.98" is kept. Returns None if nothing overlaps.
    Text is always copied verbatim — nothing is generated.
    """
    words = text.split()
    if not words:
        return None
    flags = [1 if (q_terms & set(tokenize(w))) else 0 for w in words]
    if not any(flags):
        return None

    window = min(window_words, len(words))
    best_start, best_count = 0, -1
    for start in range(0, len(words) - window + 1):
        count = sum(flags[start : start + window])
        if count > best_count:
            best_count, best_start = count, start

    matched_idx = [i for i in range(best_start, best_start + window) if flags[i]]
    if matched_idx:
        center = sum(matched_idx) // len(matched_idx)
        start = max(0, min(center - window // 2, len(words) - window))
    else:
        start = best_start
    return best_count, " ".join(words[start : start + window]).strip()


def _focused_answer(question: str, chunks: List[Chunk], window_words: int = 35) -> str:
    """Pick the best focused span across the top chunks as the answer text."""
    q_terms = set(tokenize(question))
    best: Optional[Tuple[int, str]] = None
    for chunk in chunks:
        span = _focused_span(q_terms, chunk.text, window_words)
        if span and (best is None or span[0] > best[0]):
            best = span
    if best is None:
        return _excerpt(chunks[0].text)
    return best[1]


def build_citations(scored: List[ScoredChunk], question: str) -> List[Citation]:
    """Build citations whose excerpt highlights the span most relevant to the
    question (not just the chunk's opening), so the evidence is actually useful."""
    q_terms = set(tokenize(question))
    citations: List[Citation] = []
    for s in scored:
        c = s.chunk
        span = _focused_span(q_terms, c.text, window_words=45)
        if span and len(span[1]) < len(c.text.strip()):
            excerpt = f"…{span[1]}…"
        elif span:
            excerpt = span[1]
        else:
            excerpt = _excerpt(c.text)
        citations.append(
            Citation(
                document_id=c.document_id,
                document_name=c.document.filename,
                chunk_index=c.chunk_index,
                page=c.page,
                excerpt=excerpt,
                score=s.score,
            )
        )
    return citations


def answer_question(question: str, chunks: List[Chunk], mode: str = "fast"):
    """Return (answer, abstained, mode, citations).

    mode="fast"     -> extractive engine (instant, offline, free).
    mode="thinking" -> LLM reasons on the fly; falls back to fast if no API key
                       or the call fails. The returned mode reflects what actually
                       produced the answer ("fast" | "thinking").
    """
    scored = rank_chunks(question, chunks, top_k=config.TOP_K)
    top_score = scored[0].score if scored else 0.0

    # Anti-hallucination guard #1: the best evidence must clear a score floor.
    if not scored or top_score < config.SCORE_THRESHOLD:
        logger.info("Abstain (low score %.3f) for question: %s", top_score, question)
        return config.ABSTAIN_MESSAGE, True, mode, []

    # Anti-hallucination guard #2: term coverage. A genuine answer normally
    # shares at least two distinct content words with the source. This stops a
    # single incidental word overlap (e.g. asking for a "social security number"
    # and matching only the word "number") from producing a confident answer.
    q_terms = set(tokenize(question))
    evidence_terms: Set[str] = set()
    for s in scored:
        evidence_terms |= set(tokenize(s.chunk.text))
    matched = len(q_terms & evidence_terms)
    required = min(2, len(q_terms))  # 1-word questions only need 1 match
    if matched < required:
        logger.info(
            "Abstain (weak coverage %d/%d) for question: %s",
            matched,
            len(q_terms),
            question,
        )
        return config.ABSTAIN_MESSAGE, True, mode, []

    # Keep only chunks that carry real signal for the citations/context.
    relevant = [s for s in scored if s.score >= config.SCORE_THRESHOLD] or scored[:1]
    citations = build_citations(relevant, question)

    # Thinking mode: let the LLM reason over the same grounded context.
    if mode == "thinking":
        contexts = [s.chunk.text for s in relevant]
        llm_answer = llm.synthesize(question, contexts)
        if llm_answer:
            abstained = llm_answer.strip() == config.ABSTAIN_MESSAGE
            return llm_answer, abstained, "thinking", ([] if abstained else citations)
        # No key / call failed -> transparently fall back to the fast engine.
        logger.info("Thinking unavailable; using fast (extractive) for: %s", question)

    answer = _focused_answer(question, [s.chunk for s in relevant])
    return answer, False, "fast", citations
