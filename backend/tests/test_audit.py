"""Audit endpoint tests — an evidence-backed checklist over a document.

The audit reuses the /ask retrieval + abstention gate, so a check is "supported"
only when the document genuinely backs it (with a citation), and "unsupported"
when the field is missing. Tests run on pure TF-IDF (conftest disables embeddings),
so they are deterministic.
"""

# A complete invoice: states a total, due date, terms, and number — but NO late
# fee and NO tax, so those two checks must come back unsupported.
_INVOICE = (
    b"Invoice Number INV-2025-0473. Issue Date March 3 2025. "
    b"Due Date April 2 2025. Total Amount Due $2,413.98. "
    b"Payment terms net 30 days. Bill to Acme Corporation."
)

# An invoice with incidental words that overlap the tax/due-date QUERIES
# ("Sales", "Charged", "Due" in "Amount Due") but genuinely has NO tax and NO due
# date. The audit must NOT mark those fields supported off incidental overlaps.
_TRAP_INVOICE = (
    b"Invoice INV-99. Sales representative John handled this order. "
    b"Total Amount Due $5,000.00. Charged to account 12 on file. "
    b"Percentage discount none."
)


def _upload(client, name, content):
    res = client.post(
        "/documents/upload", files={"file": (name, content, "text/plain")}
    )
    assert res.status_code == 200, res.text
    return res.json()


def _by_type(findings):
    return {f["type"]: f for f in findings}


def test_invoice_audit_finds_total_due_date_and_terms(client):
    doc = _upload(client, "invoice.txt", _INVOICE)
    res = client.post(
        "/audit", json={"document_id": doc["id"], "audit_type": "invoice"}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    findings = _by_type(body["findings"])

    # The three core invoice fields are present and each carries a citation.
    for key in ("total_amount", "due_date", "payment_terms"):
        f = findings[key]
        assert f["citation"] is not None, f"{key} should be supported: {f}"
        assert f["evidence"]
    # The extracted total is the real, verbatim value from the doc — never invented.
    assert "2,413.98" in findings["total_amount"]["claim"]
    assert body["risk_level"] in ("low", "medium", "high")
    assert body["summary"]


def test_audit_flags_unsupported_missing_field(client):
    doc = _upload(client, "invoice.txt", _INVOICE)
    body = client.post(
        "/audit", json={"document_id": doc["id"], "audit_type": "invoice"}
    ).json()
    findings = _by_type(body["findings"])

    # The invoice states no late fee and no tax -> unsupported, no citation.
    for key in ("late_fee", "tax"):
        f = findings[key]
        assert f["citation"] is None, f"{key} should be unsupported: {f}"
        assert f["evidence"] == ""
        assert f["claim"].startswith("No ")
    assert body["metrics"]["unsupported_findings"] >= 1


def test_audit_citation_coverage_matches_supported_ratio(client):
    doc = _upload(client, "invoice.txt", _INVOICE)
    body = client.post(
        "/audit", json={"document_id": doc["id"], "audit_type": "invoice"}
    ).json()
    m = body["metrics"]

    assert m["findings_count"] == len(body["findings"])
    assert m["supported_findings"] + m["unsupported_findings"] == m["findings_count"]
    expected = round(m["supported_findings"] / m["findings_count"], 2)
    assert m["citation_coverage"] == expected
    assert 0.0 < m["citation_coverage"] <= 1.0

    # Coverage is grounded: every counted "supported" finding really has a citation.
    supported = [f for f in body["findings"] if f["citation"] is not None]
    assert len(supported) == m["supported_findings"]


def test_audit_default_type_is_general(client):
    doc = _upload(client, "invoice.txt", _INVOICE)
    # audit_type omitted -> defaults to "general"; response shape is intact.
    body = client.post("/audit", json={"document_id": doc["id"]}).json()
    assert body["metrics"]["findings_count"] == len(body["findings"])
    assert body["risk_level"] in ("low", "medium", "high")


def test_audit_does_not_falsely_support_absent_fields(client):
    # Incidental query-word overlaps ("Sales"/"Charged"/"Due") must NOT make an
    # absent field look present — that would inflate coverage and lower the risk.
    doc = _upload(client, "trap.txt", _TRAP_INVOICE)
    body = client.post(
        "/audit", json={"document_id": doc["id"], "audit_type": "invoice"}
    ).json()
    findings = _by_type(body["findings"])
    assert findings["tax"]["citation"] is None, findings["tax"]
    assert findings["due_date"]["citation"] is None, findings["due_date"]
    # The total IS genuinely present -> still supported (no over-correction).
    assert findings["total_amount"]["citation"] is not None
    # A missing high-severity field (due_date) must escalate the risk.
    assert body["risk_level"] == "high"


def test_audit_on_missing_document_returns_404(client):
    res = client.post(
        "/audit", json={"document_id": 9999, "audit_type": "invoice"}
    )
    assert res.status_code == 404


def test_audit_detects_tax_in_sample_invoice(client):
    # Regression for the live bug: sample_invoice.txt contains "Tax (8.25%) $183.98"
    # but the audit reported "No tax found". The regex extractor must detect it.
    client.post("/demo/seed")
    inv = next(
        d for d in client.get("/documents").json() if d["filename"] == "sample_invoice.txt"
    )
    body = client.post(
        "/audit", json={"document_id": inv["id"], "audit_type": "invoice"}
    ).json()
    findings = _by_type(body["findings"])
    tax = findings["tax"]
    assert tax["citation"] is not None, tax
    assert "183.98" in tax["claim"]
    assert "8.25%" in (tax["claim"] + tax["evidence"])
    # The real invoice also has a total, due date, terms, number, and late fee.
    for key in ("total_amount", "due_date", "payment_terms", "invoice_number", "late_fee"):
        assert findings[key]["citation"] is not None, findings[key]


def test_ask_returns_direct_total_amount_answer(client):
    # /ask must give a crisp grounded answer, not a long raw chunk.
    client.post("/demo/seed")
    inv = next(
        d for d in client.get("/documents").json() if d["filename"] == "sample_invoice.txt"
    )
    res = client.post(
        "/ask", json={"document_id": inv["id"], "question": "What is the total amount due?"}
    ).json()
    assert res["answer"] == "The total amount due is $2,413.98."
    assert res["abstained"] is False
    assert len(res["citations"]) >= 1  # citations unchanged


def test_contract_audit_detects_fuzzy_clauses(client):
    # The fuzzy (retrieval + discriminator) path still finds clause fields.
    client.post("/demo/seed")
    contract = next(
        d for d in client.get("/documents").json()
        if d["filename"] == "sample_vendor_contract.txt"
    )
    body = client.post(
        "/audit", json={"document_id": contract["id"], "audit_type": "contract"}
    ).json()
    findings = _by_type(body["findings"])
    for key in ("payment_terms", "termination", "liability", "governing_law"):
        assert findings[key]["citation"] is not None, findings[key]


def test_audit_cannot_access_another_users_document(client, second_client):
    # Per-user scoping: a different user must not be able to audit (or even learn
    # of) someone else's private document — it 404s, never 403/leaks.
    doc = _upload(client, "private.txt", _INVOICE)
    res = second_client.post(
        "/audit", json={"document_id": doc["id"], "audit_type": "invoice"}
    )
    assert res.status_code == 404
