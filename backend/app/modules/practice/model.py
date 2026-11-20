import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    company: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    hints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reference_links: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PUBLISHED",
    )  # DRAFT, REVIEW, VERIFIED, PUBLISHED, ARCHIVED

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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


class PracticeSet(Base):
    __tablename__ = "practice_sets"

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

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    subtopic: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Intermediate",
    )

    role: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    company: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=45,
    )

    attempt_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
        onupdate=datetime.utcnow,
    )

    # Relationships
    questions = relationship("PracticeSetQuestion", back_populates="practice_set", cascade="all, delete-orphan", order_by="PracticeSetQuestion.order_index")
    attempts = relationship("PracticeSetAttempt", back_populates="practice_set", cascade="all, delete-orphan")


class PracticeSetQuestion(Base):
    __tablename__ = "practice_set_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("practice_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    practice_set = relationship("PracticeSet", back_populates="questions")
    question = relationship("PracticeQuestion")


class PracticeSetAttempt(Base):
    __tablename__ = "practice_set_attempts"

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

    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    max_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    responses: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed",
    )  # in_progress, completed, abandoned

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    practice_set = relationship("PracticeSet", back_populates="attempts")


