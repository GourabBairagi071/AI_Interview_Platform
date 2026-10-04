import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PracticeProgress(Base):
    __tablename__ = "practice_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    question_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    solved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    bookmarked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_practice"),
    )


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    technology: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    technology_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    topic_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    subtopic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Technical",
    )

    role: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="canonical",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_practice_questions_tech_topic", "technology_slug", "topic_slug"),
    )

