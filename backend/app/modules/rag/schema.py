from typing import Any
from pydantic import BaseModel, Field


class RetrievedQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str = "Technical"
    role: str | None = None
    difficulty: str
    topic: str
    skills: list[str] = Field(default_factory=list)
    company: str | None = None
    source: str = "practice_bank"
    similarity: float = 0.0
    relevance_score: float = 0.0
    role_match: bool = False
    skill_match: bool = False
    difficulty_match: bool = False


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query or skill/topic phrase")
    role: str | None = None
    difficulty: str | None = None
    topic: str | None = None
    skills: list[str] | None = None
    question_type: str | None = None
    company: str | None = None
    limit: int = Field(default=5, ge=1, le=50)
    exclude_questions: list[str] | None = Field(default=None, description="List of previously asked question texts or question_ids to exclude")


class RAGSearchResponse(BaseModel):
    query: str
    total_retrieved: int
    results: list[RetrievedQuestion]


class RAGIndexRequest(BaseModel):
    batch_size: int = Field(default=100, ge=10, le=500)
    limit: int | None = Field(default=None, ge=1, le=10000)
    force_reindex: bool = False


class RAGIndexResponse(BaseModel):
    status: str
    indexed_count: int
    skipped_count: int
    total_vectors: int


class RAGStatusResponse(BaseModel):
    status: str
    provider: str
    model_name: str
    embedding_dimension: int
    total_indexed: int
    pgvector_available: bool
