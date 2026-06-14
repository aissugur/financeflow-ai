"""Pydantic request/response models for the API."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    document_id: int
    document_name: str
    chunk_index: int
    page: Optional[int] = None
    excerpt: str
    score: float


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    error: Optional[str] = None
    num_chunks: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AskRequest(BaseModel):
    document_id: int
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    abstained: bool
    mode: str  # "extractive" or "llm"
    citations: List[Citation]


class QAOut(BaseModel):
    id: int
    document_id: int
    question: str
    answer: str
    abstained: bool
    citations: List[Citation]
    created_at: datetime


class EvalCase(BaseModel):
    question: str
    document: str
    expectation: str  # "answerable" or "should_abstain"
    expected_evidence: Optional[str] = None
    answer: str
    abstained: bool
    has_citation: bool
    evidence_found: bool  # for answerable cases: was the expected evidence cited?
    passed: bool
    citations: List[Citation]


class EvalMetrics(BaseModel):
    total_questions: int
    answered_with_citation: int
    correct_abstentions: int
    unsupported_answer_count: int
    citation_coverage: float  # cited answers / answerable questions
    evidence_match_rate: float  # expected evidence found / answerable questions
    passed: int
    accuracy: float


class EvalResponse(BaseModel):
    cases: List[EvalCase]
    metrics: EvalMetrics


class DocumentDeleted(BaseModel):
    deleted: int


class DemoSeedResponse(BaseModel):
    seeded: List[DocumentOut]
    message: str
