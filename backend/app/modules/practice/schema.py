from pydantic import BaseModel, Field


class TechnologySummary(BaseModel):
    technology: str
    slug: str
    total_questions: int
    solved: int
    remaining: int
    mastery_percentage: float
    xp_earned: int
    topics_count: int


class TechnologyListResponse(BaseModel):
    technologies: list[TechnologySummary]
    total_technologies: int
    total_questions: int
    total_solved: int


class TopicSummary(BaseModel):
    technology: str
    technology_slug: str
    topic: str
    slug: str
    total_questions: int
    solved: int
    remaining: int
    mastery_percentage: float


class TopicListResponse(BaseModel):
    technology: str
    technology_slug: str
    topics: list[TopicSummary]
    total_topics: int
    total_questions: int
    total_solved: int


class PracticeQuestionSummary(BaseModel):
    id: str
    question: str
    topic: str
    difficulty: str
    role: str | None = None
    question_type: str = "Technical"
    technology: str = "General"
    technology_slug: str = "general"
    subtopic: str = "General"
    explanation: str | None = None
    solved: bool = False
    bookmarked: bool = False
    attempts: int = 0
    xp_reward: int = 20


class PracticeQuestionListResponse(BaseModel):
    questions: list[PracticeQuestionSummary]
    total: int
    page: int
    page_size: int
    topics: list[str]
    difficulties: list[str]
    question_types: list[str]


class PracticeQuestionDetailResponse(BaseModel):
    id: str
    question: str
    topic: str
    difficulty: str
    role: str | None = None
    question_type: str = "Technical"
    technology: str = "General"
    technology_slug: str = "general"
    subtopic: str = "General"
    explanation: str = ""
    solved: bool = False
    bookmarked: bool = False
    attempts: int = 0
    xp_reward: int = 20
    last_answer: str | None = None
    last_attempted_at: str | None = None
    previous_id: str | None = None
    next_id: str | None = None



class SolveQuestionRequest(BaseModel):
    answer: str | None = None
    solved: bool = True


class SolveQuestionResponse(BaseModel):
    success: bool = True
    solved: bool
    attempts: int
    message: str
    xp_earned: int = 0
    bonus_xp: int = 0
    total_xp: int = 0
    current_level: int = 1
    level_title: str = "Novice Problem Solver"
    leveled_up: bool = False
    streak_days: int = 0
    completed_missions: list[str] = []


class BookmarkResponse(BaseModel):
    success: bool = True
    bookmarked: bool
    message: str


class TopicProgressItem(BaseModel):
    topic: str
    total: int
    solved: int
    percentage: float


class DifficultyProgressItem(BaseModel):
    difficulty: str
    total: int
    solved: int
    percentage: float


class PracticeProgressResponse(BaseModel):
    total_questions: int
    solved_count: int
    unsolved_count: int
    bookmarked_count: int
    completion_percentage: float
    topic_progress: list[TopicProgressItem]
    difficulty_progress: list[DifficultyProgressItem]


class PracticeHistoryItem(BaseModel):
    question_id: str
    question: str
    topic: str
    difficulty: str
    solved: bool
    attempts: int
    last_answer: str | None = None
    last_attempted_at: str | None = None


class PracticeHistoryResponse(BaseModel):
    history: list[PracticeHistoryItem]
    total: int


# ============================================================
# STATS: XP, MASTERY, STREAK, MISSIONS, ACHIEVEMENTS, NOTIFICATIONS
# ============================================================

class XpStats(BaseModel):
    total_xp: int
    level: int
    level_title: str
    current_level_xp: int
    next_level_xp: int
    progress_pct: float


class TopicMasteryItem(BaseModel):
    topic: str
    total: int
    solved: int
    percentage: float
    status: str  # "Unexplored" | "Practicing" | "Proficient" | "Mastered"


class MasteryStats(BaseModel):
    overall_percentage: float
    mastered_topics: int
    proficient_topics: int
    total_topics: int
    top_topics: list[TopicMasteryItem]


class StreakStats(BaseModel):
    current_streak: int
    longest_streak: int
    is_active_today: bool
    last_practiced_date: str | None = None


class PracticeMission(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    progress: int
    target: int
    completed: bool
    xp_reward: int


class PracticeAchievement(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    unlocked: bool
    progress: str
    category: str


class PracticeNotification(BaseModel):
    id: str
    type: str  # "xp_gain" | "streak" | "level_up" | "mission" | "achievement"
    title: str
    message: str
    timestamp: str
    icon: str


class PracticeStatsResponse(BaseModel):
    xp: XpStats
    mastery: MasteryStats
    streak: StreakStats
    missions: list[PracticeMission]
    achievements: list[PracticeAchievement]
    notifications: list[PracticeNotification]

