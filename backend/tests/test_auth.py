"""Authentication, protected-endpoint, and per-user isolation tests."""


def test_register_returns_token_and_no_password_hash(anon_client):
    res = anon_client.post(
        "/auth/register", json={"email": "a@b.com", "password": "password123"}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["access_token"]
    assert body["user"]["email"] == "a@b.com"
    assert "password_hash" not in body["user"]


def test_register_duplicate_returns_409(anon_client):
    payload = {"email": "dup@b.com", "password": "password123"}
    assert anon_client.post("/auth/register", json=payload).status_code == 201
    assert anon_client.post("/auth/register", json=payload).status_code == 409


def test_register_rejects_bad_email(anon_client):
    res = anon_client.post(
        "/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert res.status_code == 422


def test_register_rejects_short_password(anon_client):
    res = anon_client.post(
        "/auth/register", json={"email": "c@b.com", "password": "short"}
    )
    assert res.status_code == 422


def test_login_good_bad_and_missing(anon_client):
    anon_client.post(
        "/auth/register", json={"email": "login@b.com", "password": "password123"}
    )
    ok = anon_client.post(
        "/auth/login", json={"email": "login@b.com", "password": "password123"}
    )
    assert ok.status_code == 200 and ok.json()["access_token"]

    wrong = anon_client.post(
        "/auth/login", json={"email": "login@b.com", "password": "wrongpassword"}
    )
    assert wrong.status_code == 401

    missing = anon_client.post(
        "/auth/login", json={"email": "nobody@b.com", "password": "password123"}
    )
    assert missing.status_code == 401


def test_me_returns_current_user(client):
    res = client.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"
    assert "password_hash" not in res.json()


def test_protected_endpoints_require_a_token(anon_client):
    assert anon_client.get("/documents").status_code == 401
    assert anon_client.post(
        "/ask", json={"document_id": 1, "question": "hello?"}
    ).status_code == 401
    assert anon_client.get("/auth/me").status_code == 401


def test_invalid_token_is_rejected(anon_client):
    anon_client.headers.update({"Authorization": "Bearer not.a.real.jwt"})
    assert anon_client.get("/documents").status_code == 401


def test_public_endpoints_stay_open(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.post("/demo/seed").status_code == 200
    assert anon_client.post("/evaluate").status_code == 200


def test_documents_are_isolated_per_user(client, second_client):
    content = b"Invoice INV-9. Total Amount Due $2,413.98. Payment terms net 30."
    doc = client.post(
        "/documents/upload", files={"file": ("inv.txt", content, "text/plain")}
    ).json()
    did = doc["id"]

    # Owner sees and can use the document.
    assert any(d["id"] == did for d in client.get("/documents").json())
    assert client.get(f"/documents/{did}").status_code == 200

    # A different user cannot see it and gets 404 on every direct access.
    assert all(d["id"] != did for d in second_client.get("/documents").json())
    assert second_client.get(f"/documents/{did}").status_code == 404
    assert second_client.post(
        "/ask", json={"document_id": did, "question": "total due?"}
    ).status_code == 404
    assert second_client.delete(f"/documents/{did}").status_code == 404
