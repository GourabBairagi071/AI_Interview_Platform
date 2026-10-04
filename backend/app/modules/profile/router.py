from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.profile.schema import (
    ComprehensiveProfileResponse,
    ProfileUpdateRequest,
)
from app.modules.profile.service import ProfileService

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


@router.get(
    "",
    response_model=ComprehensiveProfileResponse,
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns complete profile and real verified statistics for authenticated user.
    """
    return await ProfileService.get_comprehensive_profile(
        db=db,
        current_user=current_user,
    )


@router.patch(
    "",
    response_model=ComprehensiveProfileResponse,
)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates editable profile fields with server-side validation and returns updated profile.
    Protected fields (user_id, email, XP, levels, streak, achievements) cannot be manipulated.
    """
    return await ProfileService.update_profile(
        db=db,
        current_user=current_user,
        data=data,
    )
