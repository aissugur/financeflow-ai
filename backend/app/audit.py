"""Evidence-backed document audit.

Runs a finance-specific checklist over a document and reports, per check, either
the cited value the document supports or that the field is missing. It reuses the
SAME retrieval + abstention gate as ``/ask`` (``answer_question``) to FIND
candidate evidence, then applies a field-specific discriminator before calling a
check "supported": the cited excerpt must actually contain one of the field's
keywords (e.g. a "tax"/"vat" token for the tax check, a "due date"/"payment due"
phrase for the due-date check). Without that second gate, the generic /ask
coverage rule (any two query words overlapping anywhere) would mark a field
"present" off incidental words like "Sales"/"Charged" — a false positive that
would wrongly lower the audit's risk level. So a check passes only when the
document genuinely supports the field, and the audit never invents a value.

This is intentionally simple and deterministic: no new model, no LLM required.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .answering import _focused_span, answer_question
from .models import Chunk
from .retrieval import tokenize
from .schemas import AuditMetrics, AuditResponse, Citation, Finding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Check:
    type: str  # finding type key (stable id for the UI)
    label: str  # human-readable field name (used in claims/summary)
    query: str  # question used to retrieve candidate evidence via answer_question
    severity: str  # severity to assign WHEN THE FIELD IS MISSING (low/medium/high)
    keywords: Tuple[str, ...]  # ≥1 must appear in the cited excerpt to count as present


# Checklists per audit type. `keywords` are the field's discriminators: distinctive
# (often multi-word) phrases that genuinely indicate the field is present, so an
# incidental overlap of generic query words can't pass the check. Matching is
# case-insensitive substring on the cited excerpt.
_CHECKLISTS = {
    "invoice": [
        _Check("total_amount", "total amount due", "What is the total amount due?", "high",
               ("total", "amount due", "balance due", "grand total", "amount payable")),
        _Check("due_date", "due date", "What is the payment due date?", "high",
               ("due date", "payment due", "due by", "due on", "pay by", "payable by")),
        _Check("payment_terms", "payment terms", "What are the payment terms, e.g. net 30?", "medium",
               ("net ", "payment term", "terms net", "due within", "payable within")),
        _Check("invoice_number", "invoice number", "What is the invoice number?", "low",
               ("invoice number", "invoice no", "invoice #", "inv-", "invoice id")),
        _Check("late_fee", "late fee", "What is the late fee or penalty for overdue payment?", "low",
               ("late fee", "late payment", "late charge", "overdue", "penalty", "per month", "per annum")),
        _Check("tax", "tax / VAT", "What sales tax or VAT percentage is charged?", "low",
               ("tax", "vat", "gst")),
    ],
    "contract": [
        _Check("payment_terms", "payment terms", "What are the payment terms?", "high",
               ("net ", "payment term", "payable within", "due within", "paid within")),
        _Check("termination", "termination clause", "What is the termination clause or notice period?", "medium",
               ("terminat", "notice period", "days' notice", "days notice", "may cancel", "for cause")),
        _Check("liability", "liability clause", "What is the liability, penalty, or indemnification clause?", "medium",
               ("liabilit", "indemnif", "indemnit", "damages", "limitation of")),
        _Check("renewal", "renewal terms", "Is there an automatic renewal or renewal term?", "medium",
               ("renew", "auto-renew", "automatic renewal", "renewal term")),
        _Check("governing_law", "governing law", "What is the governing law or jurisdiction?", "low",
               ("governing law", "jurisdiction", "governed by", "laws of", "venue")),
        _Check("late_fee", "late fee", "What interest or late fee applies to overdue amounts?", "low",
               ("late fee", "late charge", "overdue", "per annum", "per month", "interest on")),
    ],
    "payment_note": [
        _Check("amount", "payment amount", "What is the payment amount or outstanding balance?", "high",
               ("amount", "balance", "outstanding", "total due", "owing")),
        _Check("due_date", "due date", "What is the payment due date?", "high",
               ("due date", "payment due", "due by", "due on", "pay by")),
        _Check("overdue", "overdue status", "Is the payment overdue, and by how many days?", "medium",
               ("overdue", "past due", "days late", "days overdue", "arrears")),
        _Check("reference", "reference number", "What is the invoice or reference number?", "low",
               ("reference", "ref ", "ref:", "ref.", "invoice no", "invoice number", "inv-")),
    ],
    "general": [
        _Check("total_amount", "amount", "What is the total amount or balance?", "medium",
               ("total", "amount", "balance", "subtotal")),
        _Check("date", "key date", "What is the due date or other key date?", "medium",
               ("date", "deadline", "due")),
        _Check("payment_terms", "payment terms", "What are the payment terms?", "low",
               ("net ", "payment term", "terms")),
        _Check("parties", "parties", "Who are the parties, vendor, or customer involved?", "low",
               ("vendor", "customer", "client", "bill to", "sold to", "supplier", "between")),
    ],
}


def checklist_for(audit_type: str) -> List[_Check]:
    return _CHECKLISTS.get(audit_type) or _CHECKLISTS["general"]


def _supporting_citation(
    keywords: Tuple[str, ...], citations: List[Citation]
) -> Optional[Citation]:
    """The first cited excerpt that actually contains one of the field's
    discriminators, or None — i.e. the field really appears in the evidence."""
    for c in citations:
        low = c.excerpt.lower()
        if any(kw.strip() and kw in low for kw in keywords):
            return c
    return None


def _claim_span(keywords: Tuple[str, ...], excerpt: str, fallback: str) -> str:
    """A verbatim window of the excerpt centered on the field's discriminator, so
    the shown value is the field's region (not a dense overlap of generic words).
    Nothing is generated."""
    low = excerpt.lower()
    hit = next((kw for kw in keywords if kw.strip() and kw in low), None)
    span = _focused_span(set(tokenize(hit)), excerpt, window_words=14) if hit else None
    if span and span[1].strip():
        return span[1].strip()
    return (fallback or excerpt).strip()


def run_audit(audit_type: str, document_name: str, chunks: List[Chunk]) -> AuditResponse:
    """Run the checklist for ``audit_type`` over ``chunks`` and return the audit.

    For each check we retrieve candidate evidence via ``answer_question`` and then
    require the cited excerpt to contain the field's discriminator. Only then is
    the finding SUPPORTED (with the cited value + citation); otherwise the field
    is flagged unsupported (no citation) and takes the check's severity — a missing
    critical field drives the risk level.
    """
    findings: List[Finding] = []
    for chk in checklist_for(audit_type):
        answer, abstained, _mode, citations, _meta = answer_question(chk.query, chunks, "fast")
        cite = None if abstained else _supporting_citation(chk.keywords, citations)
        if cite is not None:
            findings.append(
                Finding(
                    type=chk.type,
                    severity="low",  # present and cited -> verified, lowest concern
                    claim=_claim_span(chk.keywords, cite.excerpt, answer),
                    evidence=cite.excerpt,
                    citation=cite,
                )
            )
        else:
            findings.append(
                Finding(
                    type=chk.type,
                    severity=chk.severity,  # missing field -> risk by importance
                    claim=f"No {chk.label} found in the document.",
                    evidence="",
                    citation=None,
                )
            )

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
