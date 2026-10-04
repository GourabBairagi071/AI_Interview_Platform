from pydantic import BaseModel


class OverallPerformance(BaseModel):
    overall_score: float | None = None
    best_score: float | None = None
    recent_score: float | None = None
    total_interviews: int = 0
    completed_interviews: int = 0
    total_questions_answered: int = 0
    score_change: float | None = None
    score_change_direction: str | None = None


class ScoreHistoryItem(BaseModel):
    interview_id: str
    date: str
    role: str
    score: float
    difficulty: str


class TopicPerformance(BaseModel):
    topic: str
    average_score: float
    question_count: int
    trend: str


class DifficultyPerformance(BaseModel):
    difficulty: str
    average_score: float | None = None
    question_count: int = 0


class InterviewHistoryItem(BaseModel):
    interview_id: str
    date: str
    role: str
    score: float | None = None
    difficulty: str
    status: str
    total_questions: int
    result_route: str


class AnalyticsOverviewResponse(BaseModel):
    overall: OverallPerformance
    score_history: list[ScoreHistoryItem]
    topic_performance: list[TopicPerformance]
    difficulty_performance: list[DifficultyPerformance]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    interview_history: list[InterviewHistoryItem]
