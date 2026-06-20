"""Database models: Document, Chunk, and QA history."""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # "pdf" or "txt"
    status = Column(String, nullable=False, default="processed")  # processed | failed
    error = Column(Text, nullable=True)
    num_chunks = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utcnow)
    # Owner of the document. NULL = a shared demo/eval document (visible to all).
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    owner = relationship("User", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    questions = relationship(
        "QA", back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index = Column(Integer, nullable=False)  # order within the document
    page = Column(Integer, nullable=True)  # 1-based page number when known
    text = Column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")


class QA(Base):
    __tablename__ = "qa_history"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    # The asker — so history is scoped per user even over shared demo documents.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    abstained = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    citations_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=_utcnow)

    document = relationship("Document", back_populates="questions")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    # Nullable: Google-only accounts have no password.
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )
