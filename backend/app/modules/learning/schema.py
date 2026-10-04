from datetime import date, datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Learning Profile Schemas
# -------------------------------------------------------------
class LearningProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    target_role: str
    target_level: str
    overall_readiness_score: float | None = None
    hours_per_week: int
    created_at: datetime
    updated_at: datetime


class LearningProfileUpdateRequest(BaseModel):
    target_role: str | None = None
    target_level: str | None = None
    hours_per_week: int | None = None


# -------------------------------------------------------------
# Skill Performance Schemas
# -------------------------------------------------------------
class SkillPerformanceItem(BaseModel):
    id: uuid.UUID | None = None
    canonical_skill: str
    category: str
    interview_score: float | None = None
    interview_attempts: int = 0
    coding_score: float | None = None
    coding_attempts: int = 0
    combined_score: float | None = None
    total_attempts: int = 0
    status: Literal["strong", "needs_practice", "weak", "unassessed"]
    confidence: Literal["high", "medium", "low", "insufficient"]
    last_assessed_at: datetime | None = None
    reason: str | None = None


class WeakTopicItem(BaseModel):
    topic: str
    category: str
    combined_score: float | None = None
    status: str
    confidence: str
    attempts: int
    priority: Literal["high", "medium", "low"]
    reason: str
    recommended_action: str


# -------------------------------------------------------------
# Roadmap Schemas
# -------------------------------------------------------------
class RoadmapItem(BaseModel):
    id: str
    title: str
    type: Literal["study", "practice", "interview", "coding"]
    topic: str
    is_completed: bool = False
    estimated_mins: int = 45
    ref_link: str | None = None


class RoadmapWeek(BaseModel):
    week_number: int
    title: str
    focus_topic: str
    priority: str
    reason: str
    items: list[RoadmapItem] = []


class LearningRoadmapResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    target_role: str
    title: str
    status: str
    progress_percentage: float
    weeks: list[RoadmapWeek] = []
    created_at: datetime
    updated_at: datetime


class RoadmapGenerateRequest(BaseModel):
    target_role: str | None = None
    target_level: str | None = None
    force_regenerate: bool = False


# -------------------------------------------------------------
# Learning Resources Schemas
# -------------------------------------------------------------
class LearningResourceItem(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    topic: str
    canonical_skill: str
    difficulty: str
    resource_type: str
    url: str | None = None
    estimated_duration_mins: int
    source: str
    quality_rating: float


# -------------------------------------------------------------
# Recommendations Schemas
# -------------------------------------------------------------
class RecommendationItem(BaseModel):
    id: uuid.UUID | str
    recommendation_type: Literal["resource", "interview", "coding", "revision"]
    title: str
    topic: str
    priority: Literal["high", "medium", "low"]
    reason: str
    metadata: dict[str, Any] = {}
    created_at: datetime | None = None


class ConsolidatedRecommendationsResponse(BaseModel):
    weak_topics: list[WeakTopicItem] = []
    resources: list[LearningResourceItem] = []
    interview_practice: list[dict[str, Any]] = []
    coding_challenges: list[dict[str, Any]] = []
    generated_at: datetime


# -------------------------------------------------------------
# Daily Practice Plan Schemas
# -------------------------------------------------------------
class DailyPlanTask(BaseModel):
    id: str
    title: str
    type: Literal["study", "interview", "coding", "revision"]
    topic: str
    duration_mins: int
    is_completed: bool = False
    ref_type: str | None = None
    ref_id: str | None = None
    action_url: str | None = None


class DailyPracticePlanResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_date: date
    items: list[DailyPlanTask] = []
    is_completed: bool
    completed_at: datetime | None = None
    progress_percentage: float = 0.0


# -------------------------------------------------------------
# Weekly Goals Schemas
# -------------------------------------------------------------
class WeeklyGoalItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    week_start_date: date
    title: str
    goal_type: str
    target_count: int
    completed_count: int
    deadline: datetime | None = None
    status: Literal["in_progress", "completed", "expired"]
    progress_percentage: float = 0.0


class WeeklyGoalCreateRequest(BaseModel):
    title: str
    goal_type: str = "practice"
    target_count: int = 5


# -------------------------------------------------------------
# Progress Tracking Schemas
# -------------------------------------------------------------
class SkillProgressTrend(BaseModel):
    canonical_skill: str
    current_score: float | None = None
    initial_score: float | None = None
    delta: float | None = None
    status: str
    attempts: int


class LearningProgressResponse(BaseModel):
    overall_readiness: float
    total_skills_assessed: int
    strong_skills_count: int
    needs_practice_count: int
    weak_skills_count: int
    roadmap_progress_pct: float
    daily_plan_completed: bool
    weekly_goals_completed_pct: float
    skills_trend: list[SkillProgressTrend] = []
    summary_message: str
