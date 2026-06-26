"""Text extraction from uploaded PDF / TXT files.

Returns a list of (page_number, page_text). For TXT we treat the whole file
as a single "page" (page=None). For PDF we return one entry per page so we can
later cite a real page number.

Optional OCR fallback: scanned/image-only PDF pages yield little or no
extractable text via pypdf. For such pages we *try* to render the page to an
image with PyMuPDF (fitz) and run pytesseract on it. This is entirely optional
and follows the same graceful-degradation pattern as the flashrank / embeddings
features: every import and call is wrapped in try/except so that if PyMuPDF,
pytesseract, or the Tesseract system binary is missing, OCR is silently skipped
and the page text stays exactly as pypdf returned it. OCR is never a hard
dependency and must never crash extraction.
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
        # Scanned/image-only pages yield ~no extractable text. Try OCR as a
        # best-effort fallback; on any failure the original text is kept.
        if len(text.strip()) < 15:
            ocr_text = _ocr_pdf_page(file_path, i - 1)
            if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
        pages.append((i, text))
    return pages


# OCR is OPTIONAL. Mirrors the flashrank/embeddings graceful-degradation
# pattern: lazy imports + broad try/except so a missing PyMuPDF, pytesseract,
# or Tesseract system binary simply means "no OCR", never a crash.
def _ocr_pdf_page(file_path: Path, page_index: int) -> str:
    """Render one PDF page to an image and OCR it. Returns "" on any failure."""
    try:
        import fitz  # PyMuPDF — lazy import; optional dependency
        import pytesseract  # lazy import; optional dependency
        from PIL import Image  # bundled with pytesseract usage
        import io

        doc = fitz.open(str(file_path))
        try:
            page = doc.load_page(page_index)
            # ~200 DPI render gives Tesseract enough detail without huge images.
            pix = page.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            return pytesseract.image_to_string(img) or ""
        finally:
            doc.close()
    except Exception:
        # PyMuPDF / pytesseract / Tesseract binary missing, or any render/OCR
        # error: silently skip OCR for this page.
        return ""
