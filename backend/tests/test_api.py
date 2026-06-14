"""End-to-end API tests using FastAPI's TestClient against an isolated DB."""
from tests.conftest import make_pdf_bytes


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_upload_valid_pdf_is_processed(client):
    pdf = make_pdf_bytes("Invoice Total Due 500 dollars")
    res = client.post(
        "/documents/upload",
        files={"file": ("invoice.pdf", pdf, "application/pdf")},
    )
    assert res.status_code == 200
    doc = res.json()
    assert doc["status"] == "processed"
    assert doc["file_type"] == "pdf"
    assert doc["num_chunks"] >= 1

    ask = client.post(
        "/ask", json={"document_id": doc["id"], "question": "What is the total due?"}
    ).json()
    assert ask["abstained"] is False
    assert len(ask["citations"]) >= 1
    assert ask["citations"][0]["page"] == 1  # PDF page number is preserved


def test_upload_validation_rejects_bad_extension(client):
    res = client.post(
        "/documents/upload",
        files={"file": ("notes.docx", b"hello", "application/octet-stream")},
    )
    assert res.status_code == 400


def test_upload_rejects_empty_file(client):
    res = client.post(
        "/documents/upload", files={"file": ("empty.txt", b"", "text/plain")}
    )
    assert res.status_code == 400


def _upload_invoice(client):
    content = (
        b"Invoice Number INV-2025-0473. Due Date April 2 2025. "
        b"Total Amount Due $2,413.98. Payment terms net 30."
    )
    res = client.post(
        "/documents/upload", files={"file": ("invoice.txt", content, "text/plain")}
    )
    assert res.status_code == 200
    return res.json()


def test_full_flow_upload_ask_history_delete(client):
    doc = _upload_invoice(client)
    assert doc["status"] == "processed"
    assert doc["num_chunks"] >= 1

    # answerable question
    ask = client.post(
        "/ask", json={"document_id": doc["id"], "question": "What is the total amount due?"}
    ).json()
    assert ask["abstained"] is False
    assert len(ask["citations"]) >= 1

    # unanswerable question -> abstain
    miss = client.post(
        "/ask",
        json={"document_id": doc["id"], "question": "What is the CEO's home address?"},
    ).json()
    assert miss["abstained"] is True
    assert miss["citations"] == []

    # history records both questions
    history = client.get(f"/history?document_id={doc['id']}").json()
    assert len(history) == 2

    # documents list contains it
    docs = client.get("/documents").json()
    assert any(d["id"] == doc["id"] for d in docs)

    # delete cascades cleanly
    assert client.delete(f"/documents/{doc['id']}").status_code == 200
    assert client.get(f"/documents/{doc['id']}").status_code == 404


def test_ask_on_missing_document_returns_404(client):
    res = client.post("/ask", json={"document_id": 9999, "question": "hello?"})
    assert res.status_code == 404


def test_evaluate_suite_passes(client):
    res = client.post("/evaluate")
    assert res.status_code == 200
    body = res.json()
    metrics = body["metrics"]
    # All golden questions should pass with zero unsupported answers.
    assert metrics["total_questions"] == len(body["cases"])
    assert metrics["passed"] == metrics["total_questions"]
    assert metrics["unsupported_answer_count"] == 0
    assert metrics["correct_abstentions"] >= 1
    assert metrics["citation_coverage"] == 1.0


def test_demo_seed_loads_samples(client):
    res = client.post("/demo/seed")
    assert res.status_code == 200
    body = res.json()
    assert len(body["seeded"]) >= 3
    assert all(d["status"] == "processed" for d in body["seeded"])
    # idempotent: a second call doesn't duplicate
    again = client.post("/demo/seed").json()
    assert len(again["seeded"]) == len(body["seeded"])
