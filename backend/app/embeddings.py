"""Optional dense (semantic) embeddings for hybrid retrieval.

Wraps fastembed (lightweight CPU/ONNX, no torch) behind a tiny, lazy interface.
Like the FlashRank reranker, it degrades gracefully: if fastembed or the model
isn't available, every call returns None and the caller falls back to pure
TF-IDF. Chunk vectors are computed once at ingest time and stored as float32
bytes on the Chunk row; the query is embedded on demand.
"""
import logging
import threading
from typing import List, Optional

import numpy as np

from . import config

logger = logging.getLogger(__name__)

_model = None
_unavailable = False
_lock = threading.Lock()


def is_enabled() -> bool:
    return config.EMBED_ENABLED


def _get_model():
    """Lazily load the embedding model once; cache the 'unavailable' verdict so we
    don't retry a failing import on every request."""
    global _model, _unavailable
    if _model is not None or _unavailable:
        return _model
    with _lock:
        if _model is not None or _unavailable:
            return _model
        try:
            from fastembed import TextEmbedding

            _model = TextEmbedding(model_name=config.EMBED_MODEL)
            logger.info("Embedding model loaded: %s", config.EMBED_MODEL)
        except Exception as exc:  # missing dep, no network for the model, etc.
            _unavailable = True
            logger.warning(
                "Embeddings unavailable (%s); retrieval uses TF-IDF only.", exc
            )
    return _model


def embed_texts(texts: List[str]) -> Optional[List[bytes]]:
    """Embed many texts -> list of float32 byte blobs (to store on Chunk rows).

    Returns None if embeddings are disabled/unavailable so ingest can simply
    store no vectors and retrieval stays lexical.
    """
    if not is_enabled() or not texts:
        return None
    model = _get_model()
    if model is None:
        return None
    try:
        vecs = list(model.embed(texts))
        return [np.asarray(v, dtype=np.float32).tobytes() for v in vecs]
    except Exception as exc:
        logger.warning("Batch embedding failed (%s); skipping vectors.", exc)
        return None


def embed_query(text: str) -> Optional[np.ndarray]:
    """Embed a single query -> a normalized float32 vector, or None."""
    if not is_enabled():
        return None
    model = _get_model()
    if model is None:
        return None
    try:
        vec = next(iter(model.embed([text])))
        return _normalize(np.asarray(vec, dtype=np.float32))
    except Exception as exc:
        logger.warning("Query embedding failed (%s).", exc)
        return None


def to_vector(blob: Optional[bytes]) -> Optional[np.ndarray]:
    """Decode a stored float32 blob back into a normalized vector."""
    if not blob:
        return None
    try:
        return _normalize(np.frombuffer(blob, dtype=np.float32))
    except Exception:
        return None


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n else v
