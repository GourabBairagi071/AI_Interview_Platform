from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ContestListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    status: str
    max_participants: int | None = None
    is_proctored: bool = False
    scoring_type: str = "ICPC"
    problems_count: int = 0
    registered_count: int = 0
    is_registered: bool = False


class ContestListResponse(BaseModel):
    contests: list[ContestListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    server_time: datetime


class ContestDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    status: str
    max_participants: int | None = None
    is_proctored: bool = False
    scoring_type: str = "ICPC"
    penalty_per_wrong_attempt_mins: int = 20
    rules: str | None = None
    allowed_languages: list[str] = ["python", "javascript", "cpp", "java"]
    problems_count: int = 0
    registered_count: int = 0
    is_registered: bool = False
    server_time: datetime
    time_to_start_seconds: int = 0
    time_remaining_seconds: int = 0


class ContestProblemItem(BaseModel):
    id: UUID
    problem_id: UUID
    order_index: int
    label: str
    title: str
    slug: str
    difficulty: str
    topic: str
    points: int
    penalty_mins: int
    time_limit_seconds: float
    is_solved: bool = False
    attempts_count: int = 0


class ContestProblemListResponse(BaseModel):
    contest_id: UUID
    contest_title: str
    status: str
    server_time: datetime
    time_remaining_seconds: int
    problems: list[ContestProblemItem]


class ContestProblemDetailResponse(BaseModel):
    id: UUID
    problem_id: UUID
    order_index: int
    label: str
    points: int
    penalty_mins: int
    title: str
    slug: str
    description: str
    difficulty: str
    topic: str
    tags: list[str] = []
    constraints: list[str] | str | None = None
    input_format: str | None = None
    output_format: str | None = None
    examples: list[dict] = []
    starter_code: dict[str, str] = {}
    supported_languages: list[str] = ["python", "javascript", "cpp", "java"]
    test_cases: list[dict] = []  # Strictly public only!
    time_limit_seconds: float = 3.0


class ContestSubmitRequest(BaseModel):
    problem_id: UUID
    language: str
    source_code: str


class ContestSubmitResponse(BaseModel):
    submission_id: UUID
    status: str
    score: float
    points_awarded: int
    execution_time: float
    passed_tests: int
    total_tests: int
    penalty_minutes: int
    current_rank: int | None = None
    total_solved: int = 0
    total_score: float = 0.0
    compile_error: str | None = None
    runtime_error: str | None = None


class ProblemPerformance(BaseModel):
    label: str
    title: str
    points: int
    solved: bool
    attempts: int
    time_taken_mins: int | None = None
    status: str = "Unattempted"


class ContestLeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    username: str
    full_name: str
    solved_count: int
    total_score: float
    penalty_minutes: int
    last_submission_at: datetime | None = None
    problem_results: dict[str, dict] = {}


class LeaderboardProblemMeta(BaseModel):
    problem_id: UUID
    label: str
    points: int


class ContestLeaderboardResponse(BaseModel):
    contest_id: UUID
    contest_title: str
    status: str
    server_time: datetime
    total_participants: int
    problems: list[LeaderboardProblemMeta] = []
    leaderboard: list[ContestLeaderboardEntry]
    user_entry: ContestLeaderboardEntry | None = None


class ContestMyStatusResponse(BaseModel):
    contest_id: UUID
    registered: bool
    attended: bool
    solved_count: int
    total_score: float
    penalty_minutes: int
    rank: int | None = None
    problems: list[ProblemPerformance] = []
    submissions: list[dict] = []


class ContestResultsResponse(BaseModel):
    contest_id: UUID
    contest_title: str
    status: str
    total_participants: int
    final_rank: int | None = None
    percentile: float | None = None
    total_score: float = 0.0
    solved_count: int = 0
    penalty_minutes: int = 0
    problems: list[ProblemPerformance] = []
    submissions: list[dict] = []


class UserContestHistoryItem(BaseModel):
    contest_id: UUID
    contest_title: str
    contest_slug: str
    start_time: datetime
    end_time: datetime
    status: str
    rank: int | None = None
    total_participants: int = 0
    solved_count: int = 0
    total_score: float = 0.0
    penalty_minutes: int = 0
    percentile: float | None = None


class UserContestHistoryResponse(BaseModel):
    contests: list[UserContestHistoryItem]
    total_contests: int
    best_rank: int | None = None
    average_rank: float | None = None
    total_problems_solved: int = 0


# Admin schemas
class AdminCreateContestProblem(BaseModel):
    problem_id: UUID
    order_index: int = 1
    label: str = "A"
    points: int = 100
    penalty_mins: int = 20
    time_limit_seconds: float = 3.0


class AdminCreateContestRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    start_time: datetime
    duration_minutes: int = 90
    is_proctored: bool = False
    scoring_type: str = "ICPC"
    penalty_per_wrong_attempt_mins: int = 20
    rules: str | None = None
    max_participants: int | None = None
    problems: list[AdminCreateContestProblem] = []
