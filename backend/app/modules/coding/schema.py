from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


DifficultyType = Literal["Easy", "Medium", "Hard"]


class ExampleCase(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class SampleTestCase(BaseModel):
    input: str
    output: str
    is_sample: bool = True


class CodingProblemListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    difficulty: str
    topic: str
    tags: list[str] = []
    company_tags: list[str] = []
    role_tags: list[str] = []
    supported_languages: list[str] = []
    is_solved: bool | None = None
    is_attempted: bool | None = None
    acceptance_rate: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CodingProblemListResponse(BaseModel):
    problems: list[CodingProblemListItem]
    items: list[CodingProblemListItem] | None = None  # Alias for large-scale arena compatibility
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class CodingProblemDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    difficulty: str
    topic: str
    tags: list[str] = []
    company_tags: list[str] = []
    role_tags: list[str] = []
    constraints: list[str] | str | None = None
    input_format: str | None = None
    output_format: str | None = None
    examples: list[dict[str, Any]] = []
    starter_code: dict[str, str] = {}
    supported_languages: list[str] = ["python", "javascript", "cpp", "java"]
    sample_test_cases: list[dict[str, Any]] = []
    expected_time_complexity: str | None = None
    expected_space_complexity: str | None = None
    hints: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class CodingProblemCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    difficulty: DifficultyType = "Medium"
    topic: str = Field(min_length=2, max_length=100)
    tags: list[str] | None = None
    company_tags: list[str] | None = None
    role_tags: list[str] | None = None
    constraints: str | None = None
    input_format: str | None = None
    output_format: str | None = None
    examples: list[dict[str, Any]] | None = None
    starter_code: dict[str, str] | None = None
    supported_languages: list[str] | None = None
    test_cases: list[dict[str, Any]] | None = None
    hidden_test_cases: list[dict[str, Any]] | None = None
    expected_time_complexity: str | None = None
    expected_space_complexity: str | None = None
    editorial: str | None = None
    hints: list[str] | None = None


# ============================================================
# EXECUTION & CUSTOM INPUT SCHEMAS
# ============================================================

class RunCodeRequest(BaseModel):
    problem_id: UUID
    language: str
    source_code: str = Field(min_length=1, max_length=65536)


class RunCustomCodeRequest(BaseModel):
    problem_id: UUID
    language: str
    source_code: str = Field(min_length=1, max_length=65536)
    custom_input: str = Field(default="", max_length=32768)


class RunCustomCodeResponse(BaseModel):
    stdout: str
    stderr: str
    runtime: float
    status: str


class TestCaseExecutionResult(BaseModel):
    test_index: int
    input: str
    expected_output: str
    actual_output: str
    passed: bool
    execution_time: float
    error: str | None = None


class RunCodeResponse(BaseModel):
    status: str
    results: list[TestCaseExecutionResult]
    total_passed: int
    total_tests: int
    compile_error: str | None = None
    runtime_error: str | None = None


class SubmitCodeRequest(BaseModel):
    problem_id: UUID
    language: str
    source_code: str = Field(min_length=1, max_length=65536)
    interview_id: UUID | None = None


class AIReviewStructure(BaseModel):
    summary: str
    strengths: list[str] = []
    issues: list[str] = []
    complexity: dict[str, str] = {"time": "O(n)", "space": "O(1)"}
    optimization_suggestions: list[str] = []


class CodingSubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    problem_id: UUID
    problem_title: str | None = None
    interview_id: UUID | None = None
    language: str
    source_code: str
    status: str
    score: float
    passed_tests: int
    total_tests: int
    execution_time: float
    compile_error: str | None = None
    runtime_error: str | None = None
    test_results: list[dict[str, Any]] = []
    complexity_time: str | None = None
    complexity_space: str | None = None
    ai_review: dict[str, Any] | None = None
    optimization_suggestions: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class CodingSubmissionListResponse(BaseModel):
    submissions: list[CodingSubmissionResponse]
    total: int


class CodingStatsResponse(BaseModel):
    total_attempted: int
    total_solved: int
    success_rate: float
    average_score: float
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    recent_submissions: list[CodingSubmissionResponse] = []
    topic_breakdown: dict[str, int] = {}


# ============================================================
# LEADERBOARD, ASSISTANT & RECOMMENDATIONS SCHEMAS
# ============================================================

class LeaderboardItem(BaseModel):
    rank: int
    user_id: UUID
    user_name: str
    problems_solved: int
    total_accepted: int
    coding_xp: int
    average_score: float
    current_streak: int


class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardItem]
    total_candidates: int
    user_rank: int | None = None


class AIAssistRequest(BaseModel):
    problem_id: UUID
    language: str
    source_code: str = Field(default="", max_length=65536)
    action: Literal[
        "explain_problem",
        "give_hint",
        "explain_error",
        "review_approach",
        "analyze_complexity",
        "suggest_optimization",
        "explain_edge_cases"
    ]
    hint_level: int = Field(default=1, ge=1, le=5)
    error_message: str | None = None


class AIAssistResponse(BaseModel):
    action: str
    content: str
    hint_level: int | None = None
    max_hints: int = 3


class PersonalizedRecommendationsResponse(BaseModel):
    weak_topics: list[str] = []
    strong_topics: list[str] = []
    recommended_problems: list[CodingProblemListItem] = []
    recommendation_reasons: list[str] = []
