from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.practice.schema import (
    BookmarkResponse,
    PracticeHistoryResponse,
    PracticeProgressResponse,
    PracticeQuestionDetailResponse,
    PracticeQuestionListResponse,
    PracticeStatsResponse,
    SolveQuestionRequest,
    SolveQuestionResponse,
    TechnologyListResponse,
    TopicListResponse,
)
from app.modules.practice.service import (
    bookmark_practice_question,
    get_practice_question_detail,
    get_practice_questions_list,
    get_technologies_summary,
    get_topics_summary,
    get_user_practice_history,
    get_user_practice_progress,
    get_user_practice_stats,
    solve_practice_question,
)

router = APIRouter(
    prefix="/practice",
    tags=["practice"],
)


@router.get(
    "/technologies",
    response_model=TechnologyListResponse,
)
async def list_technologies(
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_technologies_summary(
        db=db,
        user_id=current_user.id,
        search=search,
    )


@router.get(
    "/technologies/{tech_slug}/topics",
    response_model=TopicListResponse,
)
async def list_technology_topics(
    tech_slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_topics_summary(
        db=db,
        user_id=current_user.id,
        technology_slug=tech_slug,
    )


@router.get(
    "/questions",
    response_model=PracticeQuestionListResponse,
)
async def list_practice_questions(
    technology: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    search: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_practice_questions_list(
        db=db,
        user_id=current_user.id,
        technology=technology,
        topic=topic,
        search=search,
        difficulty=difficulty,
        question_type=question_type,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/progress",
    response_model=PracticeProgressResponse,
)
async def get_practice_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_practice_progress(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/history",
    response_model=PracticeHistoryResponse,
)
async def get_practice_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_practice_history(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/stats",
    response_model=PracticeStatsResponse,
)
async def get_practice_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_practice_stats(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/questions/{question_id}",
    response_model=PracticeQuestionDetailResponse,
)
async def get_practice_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_practice_question_detail(
        db=db,
        user_id=current_user.id,
        question_id=question_id,
    )


@router.post(
    "/questions/{question_id}/solve",
    response_model=SolveQuestionResponse,
)
async def solve_question(
    question_id: str,
    body: SolveQuestionRequest = SolveQuestionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await solve_practice_question(
        db=db,
        user_id=current_user.id,
        question_id=question_id,
        answer=body.answer,
        solved=body.solved,
    )


@router.post(
    "/questions/{question_id}/bookmark",
    response_model=BookmarkResponse,
)
async def bookmark_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await bookmark_practice_question(
        db=db,
        user_id=current_user.id,
        question_id=question_id,
        bookmarked=True,
    )


@router.delete(
    "/questions/{question_id}/bookmark",
    response_model=BookmarkResponse,
)
async def unbookmark_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await bookmark_practice_question(
        db=db,
        user_id=current_user.id,
        question_id=question_id,
        bookmarked=False,
    )
