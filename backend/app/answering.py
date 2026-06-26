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
import time
from typing import List, Optional, Set, Tuple

from . import config, embeddings, extractors, llm, reranking
from .models import Chunk
from .retrieval import ScoredChunk, hybrid_rank, rank_chunks, tokenize
from .schemas import Citation

logger = logging.getLogger(__name__)

# Cheap keyword heuristics for classifying the question. First match wins, so
# the more specific intents (invoice total, payment terms) are checked before
# the generic "amount"/"date" buckets. Purely descriptive metadata — it never
# affects the answer or the abstention decision.
_QUESTION_TYPE_KEYWORDS = [
    ("invoice_total", ("total", "amount due", "grand total", "balance due")),
    ("payment_terms", ("payment term", "net 30", "net 60", "due in", "terms")),
    ("date", ("date", "when", "deadline", "expire", "expiry", "due date")),
    ("amount", ("amount", "price", "cost", "subtotal", "tax", "fee", "$")),
]


def _classify_question(question: str) -> str:
    """Bucket the question into a coarse type via keyword matching (metadata only)."""
    q = question.lower()
    for qtype, keywords in _QUESTION_TYPE_KEYWORDS:
        if any(kw in q for kw in keywords):
            return qtype
    return "general"


def _confidence(top_score: float, matched: int, required: int) -> float:
    """Blend the normalized top TF-IDF score with term coverage into 0..1.

    Calibrated so a solid match (top_score ~0.5 with full coverage) lands ~0.85.
    The score component saturates (top_score / 0.6, capped at 1.0) and is weighted
    60%; the coverage component (matched / required, capped at 1.0) is weighted 40%.
    """
    if required <= 0:
        return 0.0
    score_part = min(top_score / 0.6, 1.0)
    coverage_part = min(matched / required, 1.0)
    return round(0.6 * score_part + 0.4 * coverage_part, 2)


def _build_metadata(
    *,
    question_type: str,
    evidence_status: str,
    confidence: float,
    top_score: float,
    matched_terms: int,
    required_terms: int,
    retrieved_chunks: int,
    cited_chunks: int,
    requested_mode: str,
    answer_mode: str,
    start: float,
) -> dict:
    """Assemble the metadata dict guaranteed by the shared contract."""
    return {
        "question_type": question_type,
        "evidence_status": evidence_status,
        "confidence": confidence,
        "top_score": round(top_score, 2),
        "matched_terms": matched_terms,
        "required_terms": required_terms,
        "retrieved_chunks": retrieved_chunks,
        "cited_chunks": cited_chunks,
        "requested_mode": requested_mode,
        "answer_mode": answer_mode,
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }


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
        # The focused span (when present) is the verbatim substring the question
        # matched — surface it for UI highlighting. None when no overlap was found.
        match_text = span[1] if span else None
        citations.append(
            Citation(
                document_id=c.document_id,
                document_name=c.document.filename if c.document else "unknown",
                chunk_index=c.chunk_index,
                page=c.page,
                excerpt=excerpt,
                score=s.score,
                match_text=match_text,
            )
        )
    return citations


def answer_question(question: str, chunks: List[Chunk], mode: str = "fast"):
    """Return (answer, abstained, mode, citations, metadata).

    mode="fast"     -> extractive engine (instant, offline, free).
    mode="thinking" -> LLM reasons on the fly; falls back to fast if no API key
                       or the call fails. The returned mode reflects what actually
                       produced the answer ("fast" | "thinking").

    The 5th element is a metadata dict (question type, evidence status, a 0..1
    confidence blend, the gate's scores/coverage, chunk counts, modes, and the
    latency) — purely descriptive; it never alters the abstention decision below.
    """
    start = time.perf_counter()
    question_type = _classify_question(question)
    # Stage 1: TF-IDF retrieval. Pull a larger candidate pool when reranking is on.
    # The abstention DECISION (below) always runs on the original top-K TF-IDF
    # scores, so it is identical with or without reranking — as are citation
    # coverage and the unsupported-answer count. Reranking only reorders/selects
    # WHICH evidence is cited (by design the cross-encoder may promote a chunk
    # ranked outside the top-K); when flashrank is absent the cited set is the same
    # top-K TF-IDF slice as a no-rerank build. max() keeps the gate's top-K intact
    # even if RERANK_CANDIDATES is mis-set below TOP_K.
    pool_k = (
        max(config.TOP_K, config.RERANK_CANDIDATES)
        if (reranking.is_enabled() or embeddings.is_enabled())
        else config.TOP_K
    )
    scored = rank_chunks(question, chunks, top_k=pool_k)
    gate_chunks = scored[: config.TOP_K]
    top_score = gate_chunks[0].score if gate_chunks else 0.0
    q_terms = set(tokenize(question))
    required = min(2, len(q_terms))  # 1-word questions only need 1 match

    # Anti-hallucination guard #1: the best evidence must clear a score floor.
    if not gate_chunks or top_score < config.SCORE_THRESHOLD:
        logger.info("Abstain (low score %.3f) for question: %s", top_score, question)
        metadata = _build_metadata(
            question_type=question_type,
            evidence_status="abstained",
            confidence=0.0,
            top_score=top_score,
            matched_terms=0,
            required_terms=required,
            retrieved_chunks=len(scored),
            cited_chunks=0,
            requested_mode=mode,
            answer_mode=mode,
            start=start,
        )
        return config.ABSTAIN_MESSAGE, True, mode, [], metadata

    # Anti-hallucination guard #2: term coverage. A genuine answer normally
    # shares at least two distinct content words with the source. This stops a
    # single incidental word overlap (e.g. asking for a "social security number"
    # and matching only the word "number") from producing a confident answer.
    evidence_terms: Set[str] = set()
    for s in gate_chunks:
        evidence_terms |= set(tokenize(s.chunk.text))
    matched = len(q_terms & evidence_terms)
    if matched < required:
        logger.info(
            "Abstain (weak coverage %d/%d) for question: %s",
            matched,
            len(q_terms),
            question,
        )
        metadata = _build_metadata(
            question_type=question_type,
            evidence_status="abstained",
            confidence=0.0,
            top_score=top_score,
            matched_terms=matched,
            required_terms=required,
            retrieved_chunks=len(scored),
            cited_chunks=0,
            requested_mode=mode,
            answer_mode=mode,
            start=start,
        )
        return config.ABSTAIN_MESSAGE, True, mode, [], metadata

    # Stage 1b: fuse the lexical ranking with dense SEMANTIC retrieval via RRF, so
    # the cited evidence also captures chunks that match in meaning but are worded
    # differently from the question. No-op fallback to the TF-IDF order when
    # embeddings are unavailable. (The gate above already decided we answer; this
    # only chooses WHICH evidence to cite / feed the LLM.)
    ranked = hybrid_rank(question, chunks, scored, top_k=pool_k)
    # Stage 2: cross-encoder rerank the fused pool so the most relevant evidence
    # is cited first / fed to the LLM first (graceful no-op fallback when the
    # reranker is unavailable).
    relevant = reranking.rerank(question, ranked, top_k=config.TOP_K)
    citations = build_citations(relevant, question)
    confidence = _confidence(top_score, matched, required)

    # Thinking mode: let the LLM reason over the same grounded context.
    if mode == "thinking":
        contexts = [s.chunk.text for s in relevant]
        llm_answer = llm.synthesize(question, contexts)
        if llm_answer:
            abstained = llm_answer.strip() == config.ABSTAIN_MESSAGE
            final_citations = [] if abstained else citations
            metadata = _build_metadata(
                question_type=question_type,
                evidence_status="abstained" if abstained else "supported",
                confidence=0.0 if abstained else confidence,
                top_score=top_score,
                matched_terms=matched,
                required_terms=required,
                retrieved_chunks=len(scored),
                cited_chunks=len(final_citations),
                requested_mode=mode,
                answer_mode="thinking",
                start=start,
            )
            return llm_answer, abstained, "thinking", final_citations, metadata
        # No key / call failed -> transparently fall back to the fast engine.
        logger.info("Thinking unavailable; using fast (extractive) for: %s", question)

    # Prefer a crisp, grounded direct answer for common finance questions
    # ("The total amount due is $2,413.98."), extracted verbatim from the retrieved
    # chunks; fall back to the focused span when no pattern matches.
    direct = extractors.extract_direct_answer(question, [s.chunk.text for s in relevant])
    answer = direct or _focused_answer(question, [s.chunk for s in relevant])
    metadata = _build_metadata(
        question_type=question_type,
        evidence_status="supported",
        confidence=confidence,
        top_score=top_score,
        matched_terms=matched,
        required_terms=required,
        retrieved_chunks=len(scored),
        cited_chunks=len(citations),
        requested_mode=mode,
        answer_mode="fast",
        start=start,
    )
    return answer, False, "fast", citations, metadata
