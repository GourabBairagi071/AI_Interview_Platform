import uuid
from datetime import datetime, date
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningProfile(Base):
    __tablename__ = "learning_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    target_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Full Stack Developer",
    )

    target_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Mid-Level",
    )

    overall_readiness_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hours_per_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
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


class SkillPerformance(Base):
    __tablename__ = "skill_performances"

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

    canonical_skill: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Technical",
        index=True,
    )

    interview_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    interview_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    coding_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    coding_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    combined_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unassessed",
        index=True,  # "weak", "needs_practice", "strong", "unassessed"
    )

    confidence: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="insufficient",  # "high", "medium", "low", "insufficient"
    )

    last_assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    score_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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

    __table_args__ = (
        UniqueConstraint("user_id", "canonical_skill", name="uq_user_canonical_skill"),
    )


class LearningRoadmap(Base):
    __tablename__ = "learning_roadmaps"

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

    target_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",  # "active", "completed", "archived"
    )

    progress_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    weeks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
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


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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

    canonical_skill: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Intermediate",
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Documentation",  # "Documentation", "Tutorial", "Course", "Article", "Practice Set", "Video"
    )

    url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    estimated_duration_mins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Official Documentation",
    )

    quality_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=4.8,
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


class DailyPracticePlan(Base):
    __tablename__ = "daily_practice_plans"

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

    plan_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
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
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "plan_date", name="uq_user_plan_date"),
    )


class WeeklyGoal(Base):
    __tablename__ = "weekly_goals"

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

    week_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    goal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="practice",  # "interview", "coding", "learning", "revision"
    )

    target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    completed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="in_progress",  # "in_progress", "completed", "expired"
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


class LearningRecommendation(Base):
    __tablename__ = "learning_recommendations"

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

    recommendation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # "resource", "interview", "coding", "revision"
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium",  # "high", "medium", "low"
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    is_dismissed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
