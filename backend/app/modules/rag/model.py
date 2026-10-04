import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterviewQuestionVector(Base):
    __tablename__ = "interview_question_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    question_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Technical",
        index=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    skills: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    company: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="practice_bank",
    )

    embedding: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_interview_question_vectors_topic_diff", "topic", "difficulty"),
    )
