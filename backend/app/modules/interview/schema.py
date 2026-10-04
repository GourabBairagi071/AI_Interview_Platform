from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field



class InterviewCreateRequest(BaseModel):
    job_role: str = Field(..., min_length=2, max_length=255)
    difficulty: str = Field(..., min_length=2, max_length=50)
    experience_level: str | None = Field(default="Mid-Level", max_length=50)
    interview_type: str | None = Field(default="Technical", max_length=50)
    number_of_questions: int | None = Field(default=5, ge=1, le=15)


class InterviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_role: str
    difficulty: str
    status: str
    questions: str | None
    answers: str | None
    transcript: str | None
    score: float | None
    feedback: str | None
    strengths: str | None
    weaknesses: str | None
    started_at: datetime | None
    completed_at: datetime | None
    question_evaluations: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class InterviewCreateResponse(BaseModel):
    message: str
    interview: InterviewResponse


class InterviewListResponse(BaseModel):
    interviews: list[InterviewResponse]


class InterviewAnswerRequest(BaseModel):
    answers: str = Field(..., min_length=1)


class InterviewCompleteRequest(BaseModel):
    score: float = Field(..., ge=0, le=100)


class InterviewActionResponse(BaseModel):
    message: str
    interview: InterviewResponse


class FollowupQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    conversation_history: list[dict] = Field(
        default_factory=list
    )


class FollowupQuestionResponse(BaseModel):
    should_follow_up: bool
    question: str = ""
    reason: str = ""
    difficulty: str = "medium"


class TranscriptEntry(BaseModel):
    question: str
    candidate_answer: str = ""
    timestamp: str | None = None
    question_index: int
    question_type: str = "technical"
    is_followup: bool = False
    evaluation: dict | None = None


class TranscriptResponse(BaseModel):
    interview_id: UUID
    entries: list[TranscriptEntry]
    total_entries: int


class TranscriptSyncRequest(BaseModel):
    entries: list[TranscriptEntry]