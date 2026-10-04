from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.achievements.schema import (
    AchievementDetailResponse,
    AchievementListResponse,
    AchievementSummaryResponse,
)
from app.modules.achievements.service import (
    get_achievement_detail,
    get_user_achievements_list,
    get_user_achievements_summary,
)
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

router = APIRouter(
    prefix="/achievements",
    tags=["achievements"],
)


@router.get(
    "",
    response_model=AchievementListResponse,
)
async def list_achievements(
    category: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns complete achievement catalog with the authenticated user's progress & state.
    """
    return await get_user_achievements_list(
        db=db,
        user_id=current_user.id,
        category=category,
    )


@router.get(
    "/summary",
    response_model=AchievementSummaryResponse,
)
async def get_achievements_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns high-level statistics, unlock totals, and category breakdowns.
    """
    return await get_user_achievements_summary(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/{achievement_id}",
    response_model=AchievementDetailResponse,
)
async def get_single_achievement(
    achievement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns detailed achievement information for the given achievement ID.
    """
    return await get_achievement_detail(
        db=db,
        user_id=current_user.id,
        achievement_id=achievement_id,
    )
