from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

from app.modules.interview.schema import (
    FollowupQuestionRequest,
    FollowupQuestionResponse,
    InterviewActionResponse,
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewListResponse,
    InterviewResponse,
)
from app.modules.interview.service import (
    complete_interview,
    create_interview,
    get_followup_question,
    get_user_interview,
    get_user_interviews,
    save_interview_answers,
    start_interview,
)


router = APIRouter(
    prefix="/interview",
    tags=["Interview"],
)


@router.post(
    "",
    response_model=InterviewCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_interview(
    data: InterviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        interview = await create_interview(
            db=db,
            user_id=current_user.id,
            job_role=data.job_role,
            difficulty=data.difficulty,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "message": "Interview created successfully",
        "interview": interview,
    }


@router.get(
    "",
    response_model=InterviewListResponse,
)
async def list_interviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interviews = await get_user_interviews(
        db,
        current_user.id,
    )

    return {
        "interviews": interviews,
    }


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
)
async def get_interview(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db,
        current_user.id,
        interview_id,
    )

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    return interview


@router.post(
    "/{interview_id}/start",
    response_model=InterviewActionResponse,
)
async def start_existing_interview(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db,
        current_user.id,
        interview_id,
    )

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed interview cannot be started again",
        )

    interview = await start_interview(
        db,
        interview,
    )

    return {
        "message": "Interview started successfully",
        "interview": interview,
    }


@router.post(
    "/{interview_id}/answers",
    response_model=InterviewActionResponse,
)
async def submit_answers(
    interview_id: UUID,
    data: InterviewAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db,
        current_user.id,
        interview_id,
    )

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview.status != "started":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be started before submitting answers",
        )

    interview = await save_interview_answers(
        db,
        interview,
        data.answers,
    )

    return {
        "message": "Answers saved successfully",
        "interview": interview,
    }


@router.post(
    "/{interview_id}/complete",
    response_model=InterviewActionResponse,
)
async def complete_existing_interview(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db,
        current_user.id,
        interview_id,
    )

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview.status != "started":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a started interview can be completed",
        )

    try:
        interview = await complete_interview(
            db,
            interview,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "message": "Interview completed successfully",
        "interview": interview,
    }

@router.post(
    "/{interview_id}/followup",
    response_model=FollowupQuestionResponse,
)
async def generate_followup(
    interview_id: UUID,
    data: FollowupQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await get_user_interview(
        db,
        current_user.id,
        interview_id,
    )

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    if interview.status != "started":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview must be started before generating follow-up questions",
        )

    try:
        result = await get_followup_question(
            job_role=interview.job_role,
            question=data.question,
            answer=data.answer,
            conversation_history=data.conversation_history,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return result