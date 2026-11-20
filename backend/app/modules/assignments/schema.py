import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CreateAssignmentRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    assignment_type: str = Field(
        description="QUESTION, CODING_PROBLEM, PRACTICE_SET, MOCK_TEST, AI_INTERVIEW, INTERVIEW_TEMPLATE, RESOURCE, ROADMAP, COMPANY_PREPARATION, CONTEST, CUSTOM_TASK, ASSESSMENT"
    )
    content_id: str | None = None
    content_payload: dict[str, Any] = Field(default_factory=dict)
    instructions: str | None = None
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    target_type: str = Field(
        default="INDIVIDUAL",
        description="INDIVIDUAL, GROUP, ROLE, SKILL, SUBSCRIPTION_TIER, COMPANY, SEGMENT, ALL",
    )
    target_filter: dict[str, Any] = Field(default_factory=dict)
    scheduled_for: datetime | None = None
    start_date: datetime | None = None
    due_date: datetime | None = None
    time_limit_mins: int | None = None
    attempt_limit: int = 1
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class UpdateAssignmentStatusRequest(BaseModel):
    status: str = Field(description="DRAFT, SCHEDULED, ASSIGNED, COMPLETED, EXPIRED, ARCHIVED")


class CandidateAssignmentItem(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    title: str
    description: str | None = None
    assignment_type: str
    content_id: str | None = None
    content_payload: dict[str, Any] = Field(default_factory=dict)
    instructions: str | None = None
    priority: str
    status: str
    progress_percent: float
    score: float | None = None
    attempt_count: int
    attempt_limit: int
    due_date: datetime | None = None
    time_limit_mins: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AssignmentProgressDetail(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    candidate_email: str | None = None
    status: str
    progress_percent: float
    score: float | None = None
    attempt_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    submission_ref_id: str | None = None
    created_at: datetime


class AdminAssignmentDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    assignment_type: str
    content_id: str | None = None
    content_payload: dict[str, Any] = Field(default_factory=dict)
    instructions: str | None = None
    priority: str
    target_type: str
    target_filter: dict[str, Any] = Field(default_factory=dict)
    status: str
    scheduled_for: datetime | None = None
    due_date: datetime | None = None
    time_limit_mins: int | None = None
    attempt_limit: int
    created_at: datetime
    updated_at: datetime
    
    # Aggregated metrics
    total_assigned: int
    total_started: int
    total_completed: int
    total_pending: int
    total_expired: int
    completion_rate: float
    avg_score: float | None = None
    recipients: list[AssignmentProgressDetail] = Field(default_factory=list)


class SubmitAssignmentRequest(BaseModel):
    score: float | None = None
    submission_ref_id: str | None = None
    submission_data: dict[str, Any] = Field(default_factory=dict)


class AssignmentAnalyticsResponse(BaseModel):
    total_assignments: int
    active_assignments: int
    completed_assignments: int
    total_task_dispatches: int
    overall_completion_rate: float
    avg_assignment_score: float | None = None
    by_type: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
