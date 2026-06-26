"""Evidence-backed document audit.

Runs a finance-specific checklist over a document and reports, per check, either
the cited value the document supports or that the field is missing. Two grounded
detection strategies (neither invents a value):

  * Structured fields (totals, due dates, terms, tax, invoice numbers, late fees,
    overdue days) are detected by deterministic regex extractors over the document
    chunks — precise, and finds a value even where the generic /ask retrieval gate
    would abstain (e.g. a lone "Tax (8.25%) $183.98" line, the live bug this fixes).
  * Fuzzy clauses (termination, liability, renewal, governing law, parties) have no
    clean regex, so they are detected by scanning the chunks for the clause's
    discriminator keywords and citing the surrounding text.

Both paths are deterministic (no model, no retrieval gate). A check that finds
nothing is an *unsupported* finding; a missing critical field drives the risk.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import extractors
from .models import Chunk
from .schemas import AuditMetrics, AuditResponse, Citation, Finding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Check:
    type: str  # finding type key (stable id for the UI)
    label: str  # human-readable field name (used in claims/summary)
    query: str  # short description of what the check looks for
    severity: str  # severity to assign WHEN THE FIELD IS MISSING (low/medium/high)
    extractor: Optional[str] = None  # regex extractor key (structured fields)
    keywords: Tuple[str, ...] = field(default_factory=tuple)  # discriminators (fuzzy clauses)


# Checklists per audit type. Structured fields set `extractor`; fuzzy clauses set
# `keywords` (distinctive phrases whose presence indicates the clause).
_CHECKLISTS = {
    "invoice": [
        _Check("total_amount", "total amount due", "total amount due", "high", extractor="total_amount"),
        _Check("due_date", "due date", "payment due date", "high", extractor="due_date"),
        _Check("payment_terms", "payment terms", "payment terms", "medium", extractor="payment_terms"),
        _Check("invoice_number", "invoice number", "invoice number", "low", extractor="invoice_number"),
        _Check("late_fee", "late fee", "late fee for overdue payment", "low", extractor="late_fee"),
        _Check("tax", "tax / VAT", "sales tax or VAT", "low", extractor="tax"),
    ],
    "contract": [
        _Check("payment_terms", "payment terms", "payment terms", "high", extractor="payment_terms"),
        _Check("termination", "termination clause", "termination clause or notice period", "medium",
               keywords=("terminat", "notice period", "days' notice", "days notice", "may cancel", "for cause")),
        _Check("liability", "liability clause", "liability or indemnification clause", "medium",
               keywords=("liabilit", "indemnif", "indemnit", "limitation of")),
        _Check("renewal", "renewal terms", "automatic renewal or renewal term", "medium",
               keywords=("renew", "auto-renew", "automatic renewal", "renewal term")),
        _Check("governing_law", "governing law", "governing law or jurisdiction", "low",
               keywords=("governing law", "jurisdiction", "governed by", "laws of", "venue")),
        _Check("late_fee", "late fee", "interest or late fee on overdue amounts", "low", extractor="late_fee"),
    ],
    "payment_note": [
        _Check("amount", "outstanding amount", "outstanding balance", "high", extractor="amount"),
        _Check("due_date", "due date", "payment due date", "high", extractor="due_date"),
        _Check("overdue", "overdue status", "days overdue", "medium", extractor="overdue"),
        _Check("reference", "reference number", "invoice or reference number", "low", extractor="reference"),
    ],
    "general": [
        _Check("total_amount", "amount", "total amount or balance", "medium", extractor="total_amount"),
        _Check("date", "key date", "due date or key date", "medium", extractor="date"),
        _Check("payment_terms", "payment terms", "payment terms", "low", extractor="payment_terms"),
        _Check("parties", "parties", "parties, vendor, or customer", "low",
               keywords=("vendor", "customer", "client", "bill to", "sold to", "supplier", "between")),
    ],
}


def checklist_for(audit_type: str) -> List[_Check]:
    return _CHECKLISTS.get(audit_type) or _CHECKLISTS["general"]


def _excerpt_around(text: str, pos: int, length: int, pad: Tuple[int, int] = (55, 95)) -> str:
    """A readable, ellipsised window of `text` around [pos, pos+length)."""
    s, e = max(0, pos - pad[0]), min(len(text), pos + length + pad[1])
    return ("…" if s > 0 else "") + text[s:e].strip() + ("…" if e < len(text) else "")


def _citation(chunk: Chunk, excerpt: str, match_text: str) -> Citation:
    return Citation(
        document_id=chunk.document_id,
        document_name=chunk.document.filename if chunk.document else "unknown",
        chunk_index=chunk.chunk_index,
        page=chunk.page,
        excerpt=excerpt,
        score=1.0,  # exact match -> full confidence
        match_text=match_text,
    )


def _citation_for_span(chunk: Chunk, span: str) -> Citation:
    """Citation around a verbatim regex-matched span within a chunk."""
    pos = chunk.text.lower().find(span.lower())
    excerpt = span if pos < 0 else _excerpt_around(chunk.text, pos, len(span), pad=(50, 50))
    return _citation(chunk, excerpt, span)


def _find_clause(keywords: Tuple[str, ...], chunks: List[Chunk]):
    """First (chunk, position, keyword_len) where a discriminator keyword appears."""
    for c in chunks:
        low = c.text.lower()
        for kw in keywords:
            k = kw.strip().lower()
            if k:
                pos = low.find(k)
                if pos != -1:
                    return c, pos, len(k)
    return None


def _supported(type_: str, claim: str, evidence: str, citation: Citation) -> Finding:
    return Finding(type=type_, severity="low", claim=claim, evidence=evidence, citation=citation)


def _missing(chk: _Check) -> Finding:
    return Finding(
        type=chk.type,
        severity=chk.severity,
        claim=f"No {chk.label} found in the document.",
        evidence="",
        citation=None,
    )


def run_audit(audit_type: str, document_name: str, chunks: List[Chunk]) -> AuditResponse:
    """Run the checklist for ``audit_type`` over ``chunks`` and return the audit."""
    findings: List[Finding] = []
    chunk_texts = [c.text for c in chunks]

    for chk in checklist_for(audit_type):
        if chk.extractor:
            # Structured field: deterministic regex over the document chunks.
            hit = extractors.find_field(chk.extractor, chunk_texts)
            if hit is not None:
                idx, span, _answer = hit
                cite = _citation_for_span(chunks[idx], span)
                findings.append(_supported(chk.type, span, cite.excerpt, cite))
            else:
                findings.append(_missing(chk))
        else:
            # Fuzzy clause: scan the chunks for a discriminator keyword and cite
            # the surrounding text (no retrieval gate, so no false-negative abstain).
            found = _find_clause(chk.keywords, chunks)
            if found is not None:
                chunk, pos, klen = found
                excerpt = _excerpt_around(chunk.text, pos, klen)
                cite = _citation(chunk, excerpt, chunk.text[pos : pos + klen])
                findings.append(_supported(chk.type, excerpt, excerpt, cite))
            else:
                findings.append(_missing(chk))

    supported = [f for f in findings if f.citation is not None]
    unsupported = [f for f in findings if f.citation is None]
    coverage = round(len(supported) / len(findings), 2) if findings else 0.0
    risk = _risk_level(unsupported)

    logger.info(
        "Audit type=%s doc=%r: %d/%d supported, risk=%s",
        audit_type, document_name, len(supported), len(findings), risk,
    )
    return AuditResponse(
        summary=_summary(audit_type, document_name, findings, supported, unsupported, risk),
        risk_level=risk,
        findings=findings,
        metrics=AuditMetrics(
            findings_count=len(findings),
            supported_findings=len(supported),
            unsupported_findings=len(unsupported),
            citation_coverage=coverage,
        ),
    )


def _risk_level(unsupported: List[Finding]) -> str:
    """High if a high-severity field is missing, else medium, else low."""
    if any(f.severity == "high" for f in unsupported):
        return "high"
    if any(f.severity == "medium" for f in unsupported):
        return "medium"
    return "low"


def _summary(audit_type, name, findings, supported, unsupported, risk) -> str:
    label = audit_type.replace("_", " ")
    missing = ", ".join(f.type.replace("_", " ") for f in unsupported) or "none"
    return (
        f"Audited '{name}' as a {label}: {len(supported)} of {len(findings)} checks "
        f"supported by cited evidence, {len(unsupported)} unsupported "
        f"(missing: {missing}). Overall risk: {risk}."
    )
