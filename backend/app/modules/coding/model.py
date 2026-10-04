import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.auth.model import User  # noqa: F401
from app.modules.interview.model import Interview  # noqa: F401


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    constraints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    input_format: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output_format: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    examples: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starter_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    supported_languages: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    test_cases: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    hidden_test_cases: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    company_tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    role_tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    expected_time_complexity: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    expected_space_complexity: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    editorial: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    hints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    source_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    passed_tests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_tests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    memory_usage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    compile_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    runtime_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    test_results: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    complexity_time: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    complexity_space: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    ai_review: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    optimization_suggestions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


# Export Contest Models
from app.modules.coding.contest_model import (  # noqa: E402
    Contest,
    ContestProblem,
    ContestRegistration,
    ContestSubmission,
    ContestParticipantStats,
)
