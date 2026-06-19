"""Optional second-stage reranking (cross-encoder) over retrieved chunks.

Stage 1 is the offline TF-IDF retriever (retrieval.py), which picks candidate
chunks. Stage 2 — this module — uses a small FlashRank cross-encoder to reorder
those candidates by true query relevance. The pattern is adapted from the
hybrid-search RAG examples in github.com/Shubhamsaboo/awesome-llm-apps
(Apache-2.0), re-authored to fit FinanceFlow's pipeline.

Like the LLM layer, it is OPTIONAL and degrades gracefully: if `flashrank` isn't
installed, the model can't be fetched, or anything fails, we return the original
TF-IDF order — so the app never breaks and still runs fully offline. Reranking
only reorders the evidence that gets cited and fed to the LLM; the abstention
decision still runs on the TF-IDF scores in answering.py.
"""
import logging
import threading
from typing import List

from . import config
from .retrieval import ScoredChunk

logger = logging.getLogger(__name__)

_ranker = None          # cached FlashRank Ranker instance
_unavailable = False    # latch: once we know it's unusable, stop retrying
_lock = threading.Lock()  # guards the one-time, network-bound ranker construction


def is_enabled() -> bool:
    return config.RERANK_ENABLED


def _get_ranker():
    """Lazily build and cache the FlashRank ranker, or return None if unusable.

    Construction downloads a small model on first use; FastAPI serves /ask from a
    threadpool, so the check-then-set is guarded by a lock (double-checked) to stop
    concurrent first requests from racing into two parallel downloads.
    """
    global _ranker, _unavailable
    if _ranker is not None:
        return _ranker
    if _unavailable:
        return None
    with _lock:
        if _ranker is not None:
            return _ranker
        if _unavailable:
            return None
        try:
            from flashrank import Ranker  # optional dependency, imported lazily

            _ranker = Ranker(model_name=config.RERANK_MODEL)
            logger.info("Reranker ready (%s).", config.RERANK_MODEL)
        except Exception as exc:  # not installed / download failed / offline
            logger.info("Reranker unavailable (%s); using TF-IDF order.", exc)
            _unavailable = True
    return _ranker


def rerank(question: str, scored: List[ScoredChunk], top_k: int) -> List[ScoredChunk]:
    """Reorder `scored` by cross-encoder relevance and return the top_k.

    Always safe to call: falls back to the original TF-IDF order (trimmed to
    top_k) when reranking is disabled or unavailable.
    """
    head = scored[:top_k]
    if not config.RERANK_ENABLED or len(scored) <= 1:
        return head
    ranker = _get_ranker()
    if ranker is None:
        return head
    try:
        from flashrank import RerankRequest

        # flashrank scores then sorts the passages list IN PLACE, so build a fresh
        # list every call (never cache it). Each result keeps the "id" we set here.
        passages = [{"id": i, "text": s.chunk.text} for i, s in enumerate(scored)]
        ranked = ranker.rerank(RerankRequest(query=question, passages=passages))
        # Bounds-checked remap so a changed result schema can't IndexError/KeyError.
        out = [
            scored[i]
            for r in ranked
            if isinstance((i := r.get("id")), int) and 0 <= i < len(scored)
        ]
        return (out or head)[:top_k]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Rerank failed (%s); using TF-IDF order.", exc)
        return head
