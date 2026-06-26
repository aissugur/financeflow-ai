"""Deterministic, regex-based extraction of common finance fields.

Used in two grounded places (never invents — every value is copied verbatim from
the supplied text, we only wrap it in a sentence):

  * /ask  — turn a long grounded span into a crisp direct answer
            ("The total amount due is $2,413.98.") for common finance questions,
            falling back to the existing focused-span answer when nothing matches.
  * /audit — detect a field and its verbatim value even when the generic
             retrieval gate would abstain (e.g. a lone "Tax (8.25%) $183.98"
             line that shares too few query words to clear the /ask gate).

Each extractor returns (verbatim_span, formatted_answer) or None.
"""
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

Extracted = Tuple[str, str]  # (verbatim matched span, formatted direct answer)

# A currency amount. Requires a leading "$" so a bare percentage or count can't be
# mistaken for money (e.g. "Tax 8.25%" must NOT read as "$8.25"). Cents optional.
_MONEY = r"\$\s?[\d,]+(?:\.\d{2})?"
# A date like "April 2, 2025" / "April 2 2025" or "04/02/2025".
_DATE = r"[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"


def _money(s: str) -> str:
    s = s.strip()
    return s if s.startswith("$") else "$" + s.lstrip("$ ")


def _search(text: str, pattern: str):
    return re.search(pattern, text, re.IGNORECASE)


def _ex_total(text: str) -> Optional[Extracted]:
    m = _search(text, rf"(?:total\s+amount\s+(?:due|payable)|balance\s+due|grand\s+total|total\s+(?:due|payable)|amount\s+due)\s*[:\-]?\s*({_MONEY})")
    if not m:
        return None
    return m.group(0).strip(), f"The total amount due is {_money(m.group(1))}."


def _ex_amount(text: str) -> Optional[Extracted]:
    m = _search(text, rf"(?:amount\s+outstanding|outstanding\s+balance|balance\s+outstanding|amount\s+payable|outstanding)\s*[:\-]?\s*({_MONEY})")
    if m:
        return m.group(0).strip(), f"The amount outstanding is {_money(m.group(1))}."
    return _ex_total(text)  # fall back to a stated total / amount due


def _ex_tax(text: str) -> Optional[Extracted]:
    # "Tax (8.25%) $183.98", "Sales Tax $183.98", "VAT $183.98". The % is optional
    # and the dollar amount is required, so "exclusive of applicable taxes" (no $)
    # does not register as a tax line.
    m = _search(text, rf"(?:sales\s+tax|tax|vat|gst)\b\s*(\(\s*[\d.]+\s*%\s*\))?\s*[:\-]?\s*({_MONEY})")
    if not m:
        return None
    pct = (m.group(1) or "").strip()
    answer = f"The tax is {_money(m.group(2))}" + (f" {pct}." if pct else ".")
    return m.group(0).strip(), answer


def _ex_due_date(text: str) -> Optional[Extracted]:
    m = _search(text, rf"(?:due\s+date|payment\s+due|due\s+by|pay\s+by|payable\s+by|due\s+on)\s*[:\-]?\s*({_DATE})")
    if not m:
        return None
    return m.group(0).strip(), f"The invoice due date is {m.group(1).strip()}."


def _ex_terms(text: str) -> Optional[Extracted]:
    m = _search(text, r"\bnet\s+\d{1,3}\b")
    if m:
        terms = re.sub(r"net", "Net", m.group(0), flags=re.IGNORECASE)
        return m.group(0).strip(), f"The payment terms are {terms}."
    m = _search(text, r"(?:payable|due)\s+within\s+[\w()]+\s+days")
    if m:
        return m.group(0).strip(), f"The payment terms are {m.group(0).strip()}."
    return None


def _ex_invoice_no(text: str) -> Optional[Extracted]:
    m = _search(text, r"(?:invoice\s+(?:number|no\.?|#|id)|reference)\s*[:\-]?\s*([A-Z]{2,}[-\d][A-Z0-9\-]*)")
    if not m:
        return None
    return m.group(0).strip(), f"The invoice number is {m.group(1).strip()}."


def _ex_late_fee(text: str) -> Optional[Extracted]:
    m = _search(text, r"(?:late\s+(?:fee|payment|charge)|finance\s+charge|past\s+due)[^.]{0,45}?(\d+(?:\.\d+)?\s*%(?:\s*(?:per\s+month|per\s+annum|monthly|annually))?|\$[\d,]+(?:\.\d{2})?)")
    if not m:
        return None
    return m.group(0).strip(), f"The late fee is {m.group(1).strip()}."


def _ex_overdue(text: str) -> Optional[Extracted]:
    m = _search(text, r"(\d{1,4})\s+days?\s+(?:overdue|past\s+due|late)")
    if not m:
        m = _search(text, r"days?\s+overdue\s*[:\-]?\s*(\d{1,4})")
    if not m:
        return None
    return m.group(0).strip(), f"The payment is {m.group(1)} days overdue."


def _ex_uptime(text: str) -> Optional[Extracted]:
    m = _search(text, r"uptime\s+(?:of\s+|commitment\s+(?:of\s+)?|guarantee\s+(?:of\s+)?|is\s+)?(\d{1,3}(?:\.\d+)?\s*%)")
    if not m:
        m = _search(text, r"(\d{1,3}(?:\.\d+)?\s*%)\s+(?:monthly\s+)?uptime")
    if not m:
        return None
    return m.group(0).strip(), f"The uptime commitment is {m.group(1).strip()}."


@dataclass(frozen=True)
class _Field:
    key: str
    triggers: Tuple[str, ...]  # question substrings that select this extractor
    fn: Callable[[str], Optional[Extracted]]


# Order matters: the first field whose trigger appears in the question wins, so
# specific intents (total / invoice number / due date) precede broader ones.
_FIELDS: List[_Field] = [
    _Field("total_amount", ("total amount", "amount due", "balance due", "grand total", "total due", "how much do", "how much is"), _ex_total),
    _Field("invoice_number", ("invoice number", "invoice no", "invoice #", "invoice id", "reference number"), _ex_invoice_no),
    _Field("tax", ("tax", "vat", "gst"), _ex_tax),
    _Field("due_date", ("due date", "due by", "when is", "when due", "payment due", "what date"), _ex_due_date),
    _Field("payment_terms", ("payment term", "net terms", "credit terms"), _ex_terms),
    _Field("late_fee", ("late fee", "late payment", "late charge", "finance charge", "penalty"), _ex_late_fee),
    _Field("overdue", ("overdue", "days late", "past due", "how late"), _ex_overdue),
    _Field("uptime", ("uptime", "availability", "service level", "sla"), _ex_uptime),
]

# Extractor lookup by field key (used by the audit, which knows the field up front).
_BY_KEY: dict = {
    "total_amount": _ex_total, "amount": _ex_amount, "due_date": _ex_due_date,
    "date": _ex_due_date, "payment_terms": _ex_terms, "invoice_number": _ex_invoice_no,
    "reference": _ex_invoice_no, "late_fee": _ex_late_fee, "tax": _ex_tax,
    "overdue": _ex_overdue, "uptime": _ex_uptime,
}


def extract_direct_answer(question: str, texts: List[str]) -> Optional[str]:
    """A crisp grounded answer for a common finance question, or None to let the
    caller fall back to span extraction. Only the FIRST field whose trigger words
    appear in the question is tried (across the retrieved texts, in order)."""
    q = question.lower()
    for fld in _FIELDS:
        if any(t in q for t in fld.triggers):
            for text in texts:
                res = fld.fn(text)
                if res:
                    return res[1]
            return None  # intent recognized but no value found -> fall back to span
    return None


def find_field(field_key: str, texts: List[str]) -> Optional[Tuple[int, str, str]]:
    """For the audit: return (text_index, verbatim_span, formatted_answer) for the
    first text whose extractor matches the field, or None if the field isn't found
    (or has no extractor)."""
    fn = _BY_KEY.get(field_key)
    if fn is None:
        return None
    for i, text in enumerate(texts):
        res = fn(text)
        if res:
            return i, res[0], res[1]
    return None
