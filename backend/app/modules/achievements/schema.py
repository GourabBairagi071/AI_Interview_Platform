from pydantic import BaseModel, Field


class AchievementItem(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    rarity: str = "Common"
    xp_reward: int = 25
    current_progress: int = 0
    target_progress: int = 1
    progress_percentage: float = 0.0
    unlocked: bool = False
    unlocked_at: str | None = None
    requirement_description: str | None = None


class CategoryProgress(BaseModel):
    category: str
    total: int
    unlocked: int
    percentage: float


class AchievementSummaryResponse(BaseModel):
    total_achievements: int
    unlocked_count: int
    locked_count: int
    total_xp_earned: int
    completion_percentage: float
    recent_unlocks: list[AchievementItem] = []
    categories: list[CategoryProgress] = []


class AchievementListResponse(BaseModel):
    achievements: list[AchievementItem]
    total: int
    unlocked_count: int


class AchievementDetailResponse(BaseModel):
    achievement: AchievementItem
    related_metrics: dict | None = None
