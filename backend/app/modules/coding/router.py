from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.model import User
from app.modules.coding.schema import (
    AIAssistRequest,
    AIAssistResponse,
    CodingProblemDetailResponse,
    CodingProblemListItem,
    CodingProblemListResponse,
    CodingStatsResponse,
    CodingSubmissionListResponse,
    CodingSubmissionResponse,
    LeaderboardResponse,
    PersonalizedRecommendationsResponse,
    RunCodeRequest,
    RunCodeResponse,
    RunCustomCodeRequest,
    RunCustomCodeResponse,
    SubmitCodeRequest,
)
from app.modules.coding.service import (
    format_problem_detail,
    format_submission_response,
    get_ai_assistance,
    get_coding_problem_by_id_or_slug,
    get_coding_problems,
    get_leaderboard,
    get_personalized_recommendations,
    get_submission_by_id,
    get_user_coding_stats,
    get_user_submissions,
    run_custom_code,
    run_sample_code,
    submit_code,
)

router = APIRouter(
    prefix="/coding",
    tags=["Coding Arena"],
)


@router.get(
    "/problems",
    response_model=CodingProblemListResponse,
    summary="Advanced search & filter coding problems",
)
async def list_problems(
    difficulty: str | None = Query(None, description="Filter by difficulty (Easy, Medium, Hard)"),
    topic: str | None = Query(None, description="Filter by topic"),
    tag: str | None = Query(None, description="Filter by algorithmic tag"),
    company: str | None = Query(None, description="Filter by company tag"),
    role: str | None = Query(None, description="Filter by target job role"),
    search: str | None = Query(None, description="Keyword search in title, description, topic"),
    solved: bool | None = Query(None, description="Filter by solved status"),
    attempted: bool | None = Query(None, description="Filter by attempted status"),
    sort: str | None = Query("difficulty_asc", description="Sorting (newest, oldest, title_asc, title_desc, difficulty_asc, difficulty_desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    items, total, total_pages = await get_coding_problems(
        db=db,
        difficulty=difficulty,
        topic=topic,
        tag=tag,
        company=company,
        role=role,
        search=search,
        solved=solved,
        attempted=attempted,
        sort=sort,
        page=page,
        page_size=page_size,
        current_user_id=user_id,
    )

    problem_items = [CodingProblemListItem(**it) for it in items]

    return CodingProblemListResponse(
        problems=problem_items,
        items=problem_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/problems/{id_or_slug}",
    response_model=CodingProblemDetailResponse,
    summary="Get single problem details (never exposes hidden test cases)",
)
async def get_problem_detail(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
):
    problem = await get_coding_problem_by_id_or_slug(db, id_or_slug)
    return format_problem_detail(problem)


@router.post(
    "/run",
    response_model=RunCodeResponse,
    summary="Execute code against public sample test cases",
)
async def run_code(
    payload: RunCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_sample_code(
        db=db,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
    )


@router.post(
    "/run-custom",
    response_model=RunCustomCodeResponse,
    summary="Execute code against user-supplied custom input",
)
async def run_custom(
    payload: RunCustomCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_custom_code(
        db=db,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
        custom_input=payload.custom_input,
    )


@router.post(
    "/submit",
    response_model=CodingSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit solution for full testing, deterministic scoring & AI review",
)
async def submit_solution(
    payload: SubmitCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await submit_code(
        db=db,
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
        interview_id=payload.interview_id,
    )
    problem = await get_coding_problem_by_id_or_slug(db, payload.problem_id)
    return format_submission_response(submission, problem.title)


@router.post(
    "/assist",
    response_model=AIAssistResponse,
    summary="Interactive AI coding assistance (progressive hints, approach review, complexity analysis)",
)
async def ai_assist(
    payload: AIAssistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_ai_assistance(
        db=db,
        problem_id=payload.problem_id,
        language=payload.language,
        source_code=payload.source_code,
        action=payload.action,
        hint_level=payload.hint_level,
        error_message=payload.error_message,
    )


@router.get(
    "/submissions",
    response_model=CodingSubmissionListResponse,
    summary="List candidate's submissions",
)
async def list_submissions(
    problem_id: UUID | None = Query(None, description="Optional problem filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    submissions, total = await get_user_submissions(
        db=db,
        user_id=current_user.id,
        problem_id=problem_id,
        page=page,
        page_size=page_size,
    )
    return CodingSubmissionListResponse(submissions=submissions, total=total)


@router.get(
    "/submissions/{submission_id}",
    response_model=CodingSubmissionResponse,
    summary="Get single submission by ID",
)
async def get_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_submission_by_id(db=db, submission_id=submission_id, user_id=current_user.id)


@router.get(
    "/stats",
    response_model=CodingStatsResponse,
    summary="Get candidate's coding interview performance statistics",
)
async def get_coding_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_coding_stats(db=db, user_id=current_user.id)


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Get global Coding Arena leaderboard rankings",
)
async def get_arena_leaderboard(
    limit: int = Query(50, ge=1, le=200),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    return await get_leaderboard(db=db, limit=limit, current_user_id=user_id)


@router.get(
    "/recommendations",
    response_model=PersonalizedRecommendationsResponse,
    summary="Get personalized practice recommendations based on actual performance",
)
async def get_coding_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_personalized_recommendations(db=db, user_id=current_user.id)
