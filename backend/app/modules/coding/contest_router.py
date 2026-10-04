from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.model import User
from app.modules.coding.contest_schema import (
    AdminCreateContestRequest,
    ContestDetailResponse,
    ContestLeaderboardResponse,
    ContestListResponse,
    ContestMyStatusResponse,
    ContestProblemDetailResponse,
    ContestProblemListResponse,
    ContestResultsResponse,
    ContestSubmitRequest,
    ContestSubmitResponse,
    UserContestHistoryResponse,
)
from app.modules.coding.contest_service import (
    admin_create_contest,
    get_contest_detail,
    get_contest_leaderboard,
    get_contest_problem_detail,
    get_contest_problems,
    get_contest_results,
    get_contest_user_status,
    get_contests,
    get_user_contest_history,
    register_user_for_contest,
    submit_contest_solution,
)
from app.modules.coding.schema import RunCodeRequest, RunCodeResponse, RunCustomCodeRequest, RunCustomCodeResponse
from app.modules.coding.service import run_custom_code, run_sample_code

router = APIRouter(
    prefix="/contests",
    tags=["Contest Arena"],
)


@router.get(
    "",
    response_model=ContestListResponse,
    summary="List available contests with status filters, search, and pagination",
)
async def list_contests(
    status: str | None = Query("ALL", description="Filter by status: ALL, UPCOMING, LIVE, ENDED"),
    search: str | None = Query(None, description="Search by title or description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    items, total, total_pages, server_time = await get_contests(
        db=db,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
        current_user_id=user_id,
    )
    return ContestListResponse(
        contests=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        server_time=server_time,
    )


@router.get(
    "/my-history",
    response_model=UserContestHistoryResponse,
    summary="Get user's personal contest participation history and statistics",
)
async def get_my_contest_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_contest_history(db, current_user.id)


@router.get(
    "/{id_or_slug}",
    response_model=ContestDetailResponse,
    summary="Get detailed contest information, timeline, rules, and server countdown",
)
async def get_contest(
    id_or_slug: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    return await get_contest_detail(db, id_or_slug, current_user_id=user_id)


@router.post(
    "/{contest_id}/register",
    summary="Register the current user for a contest",
)
async def register_contest(
    contest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await register_user_for_contest(db, contest_id, current_user.id)


@router.get(
    "/{contest_id}/problems",
    response_model=ContestProblemListResponse,
    summary="Get problem set for a contest (unlocked only when contest is LIVE or ENDED)",
)
async def get_problems(
    contest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_contest_problems(db, contest_id, current_user.id)


@router.get(
    "/{contest_id}/problems/{problem_id}",
    response_model=ContestProblemDetailResponse,
    summary="Get single contest problem description and public sample tests (hidden tests strictly protected)",
)
async def get_problem_detail(
    contest_id: UUID,
    problem_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_contest_problem_detail(db, contest_id, problem_id, current_user.id)


@router.post(
    "/{contest_id}/submit",
    response_model=ContestSubmitResponse,
    summary="Submit solution to contest problem (evaluates against full hidden suite and computes ICPC penalty)",
)
async def submit_solution(
    contest_id: UUID,
    payload: ContestSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await submit_contest_solution(
        db=db,
        contest_id=contest_id,
        problem_id=payload.problem_id,
        user_id=current_user.id,
        language=payload.language,
        source_code=payload.source_code,
    )


@router.post(
    "/{contest_id}/run",
    response_model=RunCodeResponse,
    summary="Execute code against sample test cases during contest",
)
async def run_contest_sample(
    contest_id: UUID,
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
    "/{contest_id}/run-custom",
    response_model=RunCustomCodeResponse,
    summary="Execute code against custom input during contest",
)
async def run_contest_custom(
    contest_id: UUID,
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


@router.get(
    "/{contest_id}/leaderboard",
    response_model=ContestLeaderboardResponse,
    summary="Get live contest leaderboard standings with penalty times and problem matrix",
)
async def get_leaderboard(
    contest_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    return await get_contest_leaderboard(db, contest_id, current_user_id=user_id)


@router.get(
    "/{contest_id}/my-status",
    response_model=ContestMyStatusResponse,
    summary="Get current user's contest progression, submissions, and problem status",
)
async def get_my_status(
    contest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_contest_user_status(db, contest_id, current_user.id)


@router.get(
    "/{contest_id}/results",
    response_model=ContestResultsResponse,
    summary="Get final contest results, official ranking, and percentile standing",
)
async def get_results(
    contest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_contest_results(db, contest_id, current_user.id)


@router.post(
    "/admin/create",
    summary="Admin architecture: create a new competitive contest",
)
async def admin_create(
    payload: AdminCreateContestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contest = await admin_create_contest(db, payload)
    return {"id": contest.id, "slug": contest.slug, "title": contest.title}
