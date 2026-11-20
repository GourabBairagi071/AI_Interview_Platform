import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CandidateAssignment(Base):
    __tablename__ = "candidate_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # QUESTION, CODING_PROBLEM, PRACTICE_SET, MOCK_TEST, AI_INTERVIEW,
    # INTERVIEW_TEMPLATE, RESOURCE, ROADMAP, COMPANY_PREPARATION, CONTEST,
    # CUSTOM_TASK, ASSESSMENT
    assignment_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    content_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Priority: LOW, MEDIUM, HIGH, URGENT
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    
    # Target Type: INDIVIDUAL, GROUP, ROLE, SKILL, SUBSCRIPTION_TIER, COMPANY, SEGMENT, ALL
    target_type: Mapped[str] = mapped_column(String(50), default="INDIVIDUAL", nullable=False)
    target_filter: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    time_limit_mins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Status: DRAFT, SCHEDULED, ASSIGNED, IN_PROGRESS, COMPLETED, EXPIRED, ARCHIVED
    status: Mapped[str] = mapped_column(String(50), default="ASSIGNED", nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    progress_records = relationship(
        "CandidateAssignmentProgress",
        back_populates="assignment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CandidateAssignmentProgress(Base):
    __tablename__ = "candidate_assignment_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Status: ASSIGNED, IN_PROGRESS, SUBMITTED, COMPLETED, EXPIRED
    status: Mapped[str] = mapped_column(String(50), default="ASSIGNED", nullable=False, index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    submission_ref_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submission_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    assignment = relationship("CandidateAssignment", back_populates="progress_records")

    __table_args__ = (
        UniqueConstraint("assignment_id", "candidate_id", name="uq_candidate_assignment_recipient"),
    )
