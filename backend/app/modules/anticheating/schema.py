from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


EventType = Literal[
    "FACE_MISSING",
    "MULTIPLE_PERSON",
    "IDENTITY_MISMATCH",
    "MOBILE_DETECTED",
    "DEVICE_DETECTED",
    "SUSPICIOUS_ABSENCE",
    "OTHER_SUSPICIOUS_ACTIVITY",
]

SeverityLevel = Literal["LOW", "MEDIUM", "HIGH"]
OverallStatus = Literal["CLEAR", "REVIEW", "SUSPICIOUS"]


class AntiCheatingEventCreateRequest(BaseModel):
    event_type: EventType
    severity: SeverityLevel = "LOW"
    timestamp: datetime | None = None
    duration: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str = Field(min_length=1)
    evidence_reference: str | None = None
    metadata: dict[str, Any] | None = None


class AntiCheatingEventResponse(BaseModel):
    id: UUID
    interview_id: UUID
    event_type: str
    severity: str
    timestamp: datetime
    duration: float
    confidence: float
    description: str
    evidence_reference: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AntiCheatingEventListResponse(BaseModel):
    events: list[AntiCheatingEventResponse]
    total: int


class AntiCheatingSummaryResponse(BaseModel):
    overall_status: OverallStatus
    total_events: int
    face_missing_events: int
    multiple_person_events: int
    identity_mismatch_events: int
    device_events: int
    total_suspicious_duration: float
    risk_score: float


class FaceRegistrationRequest(BaseModel):
    encoding: list[float] = Field(min_length=8, max_length=512)
    captured_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class FaceRegistrationResponse(BaseModel):
    registered: bool
    interview_id: UUID
    vector_dimension: int
    registered_at: datetime

