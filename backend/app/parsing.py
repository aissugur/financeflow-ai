"""Text extraction from uploaded PDF / TXT files.

Returns a list of (page_number, page_text). For TXT we treat the whole file
as a single "page" (page=None). For PDF we return one entry per page so we can
later cite a real page number.
"""
from pathlib import Path
from typing import List, Optional, Tuple

Page = Tuple[Optional[int], str]


def extract_pages(file_path: Path, file_type: str) -> List[Page]:
    if file_type == "txt":
        return _extract_txt(file_path)
    if file_type == "pdf":
        return _extract_pdf(file_path)
    raise ValueError(f"Unsupported file type: {file_type}")


def _extract_txt(file_path: Path) -> List[Page]:
    # Be forgiving about encodings; never crash on a stray byte.
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return [(None, text)]


def _extract_pdf(file_path: Path) -> List[Page]:
    from pypdf import PdfReader  # imported lazily so TXT-only users need no PDF lib

    reader = PdfReader(str(file_path))
    pages: List[Page] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((i, text))
    return pages
