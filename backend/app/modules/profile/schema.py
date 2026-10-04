import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


def validate_url_field(val: str | None) -> str | None:
    if val is None:
        return None
    val_clean = val.strip()
    if not val_clean:
        return None
    if not (val_clean.startswith("http://") or val_clean.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    if not URL_REGEX.match(val_clean):
        raise ValueError("Invalid URL format")
    return val_clean


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=1000)
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=255)
    college: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1970, le=2040)
    target_role: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    skills: str | None = Field(default=None, max_length=2000)
    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)

    @field_validator("github_url", "linkedin_url", "portfolio_url", "avatar_url")
    @classmethod
    def check_urls(cls, v: str | None) -> str | None:
        return validate_url_field(v)

    model_config = ConfigDict(extra="forbid")


class ProfileDetails(BaseModel):
    id: str
    user_id: str
    full_name: str
    email: str
    headline: str | None = None
    bio: str | None = None
    phone: str | None = None
    location: str | None = None
    college: str | None = None
    degree: str | None = None
    graduation_year: int | None = None
    target_role: str | None = None
    experience_level: str | None = None
    skills: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    avatar_url: str | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class AccountDetails(BaseModel):
    id: str
    email: str
    is_verified: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PracticeTechItem(BaseModel):
    technology: str
    slug: str
    solved: int
    total: int
    mastery_percentage: float


class PracticeSummary(BaseModel):
    questions_solved: int
    total_questions: int
    completion_percentage: float
    current_streak: int
    longest_streak: int
    total_xp: int
    current_level: int
    level_title: str
    progress_pct: float
    topics_mastered: int
    technologies_practiced: list[PracticeTechItem]


class AchievementSummary(BaseModel):
    unlocked_count: int
    total_achievements: int
    completion_percentage: float
    recent_unlocks: list[dict[str, Any]]


class RecentInterview(BaseModel):
    id: str
    job_role: str
    difficulty: str
    score: float | None
    completed_at: str | None


class InterviewSummary(BaseModel):
    completed_interviews: int
    average_score: float
    best_score: float
    recent_interview: RecentInterview | None


class ResumeStatus(BaseModel):
    has_resume: bool
    filename: str | None = None
    uploaded_at: str | None = None


class ComprehensiveProfileResponse(BaseModel):
    profile: ProfileDetails
    account: AccountDetails
    practice_summary: PracticeSummary
    achievement_summary: AchievementSummary
    interview_summary: InterviewSummary
    resume_status: ResumeStatus
