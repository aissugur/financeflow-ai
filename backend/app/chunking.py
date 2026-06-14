"""Split extracted page text into overlapping word chunks.

Simple, predictable, and fast. We keep a small overlap so a fact that sits on a
chunk boundary still appears whole in at least one chunk.
"""
import re
from typing import List, Optional, Tuple

# (page, chunk_index, text)
ChunkTuple = Tuple[Optional[int], int, str]

CHUNK_SIZE_WORDS = 120
CHUNK_OVERLAP_WORDS = 25


def _normalize(text: str) -> str:
    # Collapse whitespace so chunk sizes are stable across messy PDFs.
    return re.sub(r"\s+", " ", text).strip()


def chunk_pages(pages: List[Tuple[Optional[int], str]]) -> List[ChunkTuple]:
    chunks: List[ChunkTuple] = []
    index = 0
    step = max(1, CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS)

    for page_number, raw_text in pages:
        text = _normalize(raw_text)
        if not text:
            continue
        words = text.split(" ")
        for start in range(0, len(words), step):
            window = words[start : start + CHUNK_SIZE_WORDS]
            if not window:
                continue
            chunk_text = " ".join(window).strip()
            if len(chunk_text) < 3:
                continue
            chunks.append((page_number, index, chunk_text))
            index += 1
            if start + CHUNK_SIZE_WORDS >= len(words):
                break  # avoid an extra empty tail window

    return chunks
