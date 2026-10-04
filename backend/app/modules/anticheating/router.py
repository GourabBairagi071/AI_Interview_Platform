from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.interview.model import Interview
from app.modules.anticheating.schema import (
    AntiCheatingEventCreateRequest,
    AntiCheatingEventListResponse,
    AntiCheatingEventResponse,
    AntiCheatingSummaryResponse,
    FaceRegistrationRequest,
    FaceRegistrationResponse,
)
from app.modules.anticheating.service import (
    get_interview_events,
    get_interview_summary,
    record_anti_cheating_event,
    register_candidate_face,
)

router = APIRouter(
    prefix="/interview",
    tags=["Anti-Cheating"],
)


async def _verify_interview_ownership(
    interview_id: UUID,
    user: User,
    db: AsyncSession,
) -> Interview:
    stmt = select(Interview).where(Interview.id == interview_id)
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this interview",
        )

    return interview


@router.post(
    "/{interview_id}/anti-cheating/events",
    response_model=AntiCheatingEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    interview_id: UUID,
    data: AntiCheatingEventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_interview_ownership(interview_id, current_user, db)
    return await record_anti_cheating_event(db, interview_id, data)


@router.get(
    "/{interview_id}/anti-cheating/events",
    response_model=AntiCheatingEventListResponse,
)
async def list_events(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_interview_ownership(interview_id, current_user, db)
    events = await get_interview_events(db, interview_id)
    return AntiCheatingEventListResponse(
        events=events,
        total=len(events),
    )


@router.get(
    "/{interview_id}/anti-cheating/summary",
    response_model=AntiCheatingSummaryResponse,
)
async def get_summary(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_interview_ownership(interview_id, current_user, db)
    return await get_interview_summary(db, interview_id)


@router.post(
    "/{interview_id}/anti-cheating/register-face",
    response_model=FaceRegistrationResponse,
    status_code=status.HTTP_200_OK,
)
async def register_face(
    interview_id: UUID,
    data: FaceRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_interview_ownership(interview_id, current_user, db)
    return register_candidate_face(interview_id, data)

