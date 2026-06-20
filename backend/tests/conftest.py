"""Shared pytest fixtures.

API tests run against the real FastAPI app but with the database swapped for a
throwaway temp-file SQLite, and AUTHENTICATED by default: the `client` fixture
registers a user and presets the Authorization header, so the existing API tests
exercise the now-protected endpoints unchanged.
"""
import os
import tempfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def _engine():
    """One isolated temp-SQLite engine + get_db override, shared by every client
    in a test (so two users hit the SAME database for isolation checks)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        os.unlink(path)


def _register(c, email="user@example.com", password="password123") -> str:
    res = c.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


@pytest.fixture()
def anon_client(_engine):
    """Unauthenticated client — for auth and 401 tests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client(_engine):
    """Authenticated client (default user). Existing API tests use this, so every
    request carries a Bearer token with zero per-test changes."""
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {_register(c)}"})
        yield c


@pytest.fixture()
def second_client(_engine):
    """A DIFFERENT user on the SAME engine — for cross-user isolation tests."""
    with TestClient(app) as c:
        token = _register(c, email="other@example.com")
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


def make_chunk(text, *, chunk_index=0, page=None, filename="doc.txt", document_id=1):
    """Build a lightweight stand-in for a Chunk ORM row (no DB needed)."""
    return SimpleNamespace(
        text=text,
        chunk_index=chunk_index,
        page=page,
        document_id=document_id,
        document=SimpleNamespace(filename=filename),
    )


def make_pdf_bytes(text: str) -> bytes:
    """Build a minimal, valid single-page PDF with extractable text.

    Dependency-free (no reportlab) — assembles objects and a correct xref table
    so `pypdf` can parse it, which lets us test the real PDF upload path.
    """
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
    ]
    stream = b"BT /F1 24 Tf 72 700 Td (" + text.encode("latin-1") + b") Tj ET"
    objs.append(b"<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream")
    objs.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj" + body + b"endobj\n"
    xref_pos = len(out)
    n = len(objs) + 1
    out += b"xref\n0 " + str(n).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (
        b"trailer<</Size " + str(n).encode() + b"/Root 1 0 R>>\nstartxref\n"
        + str(xref_pos).encode()
        + b"\n%%EOF"
    )
    return bytes(out)
