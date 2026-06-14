"""Shared pytest fixtures.

The API tests run against the real FastAPI app but with the database swapped
for a throwaway temp-file SQLite, so tests never touch the dev database.
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
def client():
    """A TestClient backed by an isolated temp SQLite database."""
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
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        os.unlink(path)


def make_chunk(text, *, chunk_index=0, page=None, filename="doc.txt", document_id=1):
    """Build a lightweight stand-in for a Chunk ORM row (no DB needed)."""
    return SimpleNamespace(
        text=text,
        chunk_index=chunk_index,
        page=page,
        document_id=document_id,
        document=SimpleNamespace(filename=filename),
    )
