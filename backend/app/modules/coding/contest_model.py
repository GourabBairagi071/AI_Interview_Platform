import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Contest(Base):
    __tablename__ = "contests"

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

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UPCOMING",
        index=True,
    )  # UPCOMING, LIVE, ENDED, CANCELLED

    max_participants: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_proctored: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    scoring_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ICPC",
    )  # ICPC, POINTS, IOI

    penalty_per_wrong_attempt_mins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
    )

    rules: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    allowed_languages: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # JSON list of strings

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
    problems = relationship("ContestProblem", back_populates="contest", cascade="all, delete-orphan", order_by="ContestProblem.order_index")
    registrations = relationship("ContestRegistration", back_populates="contest", cascade="all, delete-orphan")
    submissions = relationship("ContestSubmission", back_populates="contest", cascade="all, delete-orphan")
    participants_stats = relationship("ContestParticipantStats", back_populates="contest", cascade="all, delete-orphan")


class ContestProblem(Base):
    __tablename__ = "contest_problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    label: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="A",
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    penalty_mins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
    )

    time_limit_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
    )

    __table_args__ = (
        UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
        UniqueConstraint("contest_id", "order_index", name="uq_contest_order"),
    )

    # Relationships
    contest = relationship("Contest", back_populates="problems")
    problem = relationship("CodingProblem")


class ContestRegistration(Base):
    __tablename__ = "contest_registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REGISTERED",
    )  # REGISTERED, ATTENDED, DISQUALIFIED, WITHDRAWN

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_user_reg"),
    )

    # Relationships
    contest = relationship("Contest", back_populates="registrations")
    user = relationship("User")


class ContestSubmission(Base):
    __tablename__ = "contest_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    coding_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # Accepted, Wrong Answer, Compilation Error, Runtime Error, Time Limit Exceeded

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    execution_time: Mapped[float] = mapped_column(
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

    penalty_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    contest = relationship("Contest", back_populates="submissions")
    problem = relationship("CodingProblem")
    user = relationship("User")


class ContestParticipantStats(Base):
    __tablename__ = "contest_participant_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    solved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    penalty_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    last_submission_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    problems_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # JSON summary of per-problem state {problem_id: {solved: bool, attempts: int, points: int, time_taken_mins: int}}

    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_user_stats"),
    )

    # Relationships
    contest = relationship("Contest", back_populates="participants_stats")
    user = relationship("User")
