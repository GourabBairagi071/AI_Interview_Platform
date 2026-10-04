import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.model import User
from app.modules.coding.contest_model import (
    Contest,
    ContestProblem,
    ContestRegistration,
    ContestSubmission,
    ContestParticipantStats,
)
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.coding.execution import execution_service
from app.modules.coding.service import format_problem_detail

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def get_current_utc() -> datetime:
    return datetime.now(timezone.utc)


def update_contest_status_by_time(contest: Contest, now: datetime) -> str:
    """Computes and updates contest status dynamically based on current server time."""
    if contest.status == "CANCELLED":
        return "CANCELLED"

    start = contest.start_time
    end = contest.end_time

    # Ensure timezone awareness for safe comparison
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if now < start:
        contest.status = "UPCOMING"
    elif start <= now <= end:
        contest.status = "LIVE"
    else:
        contest.status = "ENDED"

    return contest.status


# ============================================================
# SEED INITIAL CONTESTS
# ============================================================

async def seed_initial_contests(db: AsyncSession) -> None:
    """Seeds initial real contests using actual problems from the 1,000-problem bank."""
    res = await db.execute(select(func.count()).select_from(Contest))
    if res.scalar() > 0:
        return

    now = get_current_utc()

    # Fetch 12 diverse problems from database for 3 contests
    stmt = select(CodingProblem).order_by(CodingProblem.title).limit(12)
    sample_problems = (await db.execute(stmt)).scalars().all()
    if len(sample_problems) < 12:
        return

    # 1. LIVE CONTEST (Started 30m ago, ends in 60m)
    live_start = now - timedelta(minutes=30)
    live_end = now + timedelta(minutes=60)
    live_contest = Contest(
        title="Live Weekly Coding Clash #42",
        slug="live-weekly-coding-clash-42",
        description="Compete in real-time against developers worldwide. Solve 4 algorithmic challenges in 90 minutes. Strict server-enforced countdown with live rankings.",
        start_time=live_start,
        end_time=live_end,
        duration_minutes=90,
        status="LIVE",
        is_proctored=False,
        scoring_type="ICPC",
        penalty_per_wrong_attempt_mins=20,
        rules="• 4 Problems ordered from Easy to Hard.\n• 20-minute penalty per incorrect submission prior to accepted solution.\n• Tie-breaks resolved by total penalty minutes.",
        allowed_languages=json.dumps(["python", "javascript", "cpp", "java"]),
    )
    db.add(live_contest)
    await db.flush()

    for idx, prob in enumerate(sample_problems[0:4]):
        cp = ContestProblem(
            contest_id=live_contest.id,
            problem_id=prob.id,
            order_index=idx + 1,
            label=chr(65 + idx),
            points=100 * (idx + 1),
            penalty_mins=20,
        )
        db.add(cp)

    # 2. UPCOMING CONTEST (Starts in 2 days)
    up_start = now + timedelta(days=2)
    up_end = up_start + timedelta(minutes=120)
    up_contest = Contest(
        title="Global Grandmaster Invitational 2026",
        slug="global-grandmaster-invitational-2026",
        description="Premium proctored competitive coding arena contest featuring advanced data structures, graph theory, and dynamic programming.",
        start_time=up_start,
        end_time=up_end,
        duration_minutes=120,
        status="UPCOMING",
        is_proctored=True,
        scoring_type="ICPC",
        penalty_per_wrong_attempt_mins=20,
        rules="• Proctored contest: camera and tab verification required.\n• 4 Problems with comprehensive hidden test sets.\n• Official certificate issued for top 10% percentile.",
        allowed_languages=json.dumps(["python", "javascript", "cpp", "java"]),
    )
    db.add(up_contest)
    await db.flush()

    for idx, prob in enumerate(sample_problems[4:8]):
        cp = ContestProblem(
            contest_id=up_contest.id,
            problem_id=prob.id,
            order_index=idx + 1,
            label=chr(65 + idx),
            points=100 * (idx + 1),
            penalty_mins=20,
        )
        db.add(cp)

    # 3. ENDED CONTEST (Finished yesterday)
    ended_start = now - timedelta(days=1, hours=3)
    ended_end = ended_start + timedelta(minutes=90)
    ended_contest = Contest(
        title="Spring Sprint Arena Championship",
        slug="spring-sprint-arena-championship",
        description="Completed competitive contest. Explore the problem archive, review finalized leaderboards, and inspect top solutions.",
        start_time=ended_start,
        end_time=ended_end,
        duration_minutes=90,
        status="ENDED",
        is_proctored=False,
        scoring_type="ICPC",
        penalty_per_wrong_attempt_mins=20,
        rules="• Solved under standard ICPC rules.\n• Historical results and rankings preserved.",
        allowed_languages=json.dumps(["python", "javascript", "cpp", "java"]),
    )
    db.add(ended_contest)
    await db.flush()

    for idx, prob in enumerate(sample_problems[8:12]):
        cp = ContestProblem(
            contest_id=ended_contest.id,
            problem_id=prob.id,
            order_index=idx + 1,
            label=chr(65 + idx),
            points=100 * (idx + 1),
            penalty_mins=20,
        )
        db.add(cp)

    await db.commit()


# ============================================================
# CONTEST RETRIEVAL & DISCOVERY
# ============================================================

async def get_contests(
    db: AsyncSession,
    status_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    current_user_id: UUID | None = None,
) -> tuple[list[dict[str, Any]], int, int, datetime]:
    await seed_initial_contests(db)

    now = get_current_utc()
    query = select(Contest)

    # Update statuses in database where needed
    all_contests_res = await db.execute(select(Contest))
    for c in all_contests_res.scalars().all():
        old_status = c.status
        new_status = update_contest_status_by_time(c, now)
        if old_status != new_status:
            db.add(c)
    await db.commit()

    # Filter by status
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(func.upper(Contest.status) == status_filter.upper())

    # Search filter
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Contest.title).like(term),
                func.lower(Contest.description).like(term),
            )
        )

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Sort: LIVE first, then UPCOMING (asc by start), then ENDED (desc by end)
    query = query.order_by(
        case(
            (Contest.status == "LIVE", 1),
            (Contest.status == "UPCOMING", 2),
            else_=3,
        ),
        Contest.start_time.asc(),
    )

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    contests = result.scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)

    # Enrich with counts and user registration status
    items: list[dict[str, Any]] = []
    for c in contests:
        # Problem count
        prob_count_res = await db.execute(
            select(func.count()).select_from(ContestProblem).where(ContestProblem.contest_id == c.id)
        )
        prob_count = prob_count_res.scalar() or 0

        # Registration count
        reg_count_res = await db.execute(
            select(func.count()).select_from(ContestRegistration).where(ContestRegistration.contest_id == c.id)
        )
        reg_count = reg_count_res.scalar() or 0

        # User registered?
        is_reg = False
        if current_user_id:
            user_reg_res = await db.execute(
                select(ContestRegistration.id).where(
                    ContestRegistration.contest_id == c.id,
                    ContestRegistration.user_id == current_user_id,
                )
            )
            is_reg = user_reg_res.first() is not None

        items.append({
            "id": c.id,
            "title": c.title,
            "slug": c.slug,
            "description": c.description,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "duration_minutes": c.duration_minutes,
            "status": c.status,
            "max_participants": c.max_participants,
            "is_proctored": c.is_proctored,
            "scoring_type": c.scoring_type,
            "problems_count": prob_count,
            "registered_count": reg_count,
            "is_registered": is_reg,
        })

    return items, total, total_pages, now


async def get_contest_by_id_or_slug(db: AsyncSession, id_or_slug: str | UUID) -> Contest:
    await seed_initial_contests(db)

    now = get_current_utc()
    contest: Contest | None = None
    try:
        val_uuid = id_or_slug if isinstance(id_or_slug, UUID) else UUID(str(id_or_slug))
        res = await db.execute(select(Contest).where(Contest.id == val_uuid))
        contest = res.scalar_one_or_none()
    except (ValueError, AttributeError):
        res = await db.execute(select(Contest).where(Contest.slug == str(id_or_slug)))
        contest = res.scalar_one_or_none()

    if not contest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contest '{id_or_slug}' not found.",
        )

    # Sync status
    update_contest_status_by_time(contest, now)
    return contest


async def get_contest_detail(
    db: AsyncSession,
    id_or_slug: str | UUID,
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, id_or_slug)
    now = get_current_utc()

    # Ensure start/end tz awareness
    start = contest.start_time.replace(tzinfo=timezone.utc) if contest.start_time.tzinfo is None else contest.start_time
    end = contest.end_time.replace(tzinfo=timezone.utc) if contest.end_time.tzinfo is None else contest.end_time

    time_to_start = max(0, int((start - now).total_seconds()))
    time_remaining = max(0, int((end - now).total_seconds())) if contest.status == "LIVE" else 0

    prob_count_res = await db.execute(
        select(func.count()).select_from(ContestProblem).where(ContestProblem.contest_id == contest.id)
    )
    prob_count = prob_count_res.scalar() or 0

    reg_count_res = await db.execute(
        select(func.count()).select_from(ContestRegistration).where(ContestRegistration.contest_id == contest.id)
    )
    reg_count = reg_count_res.scalar() or 0

    is_reg = False
    if current_user_id:
        user_reg_res = await db.execute(
            select(ContestRegistration.id).where(
                ContestRegistration.contest_id == contest.id,
                ContestRegistration.user_id == current_user_id,
            )
        )
        is_reg = user_reg_res.first() is not None

    allowed_langs = json.loads(contest.allowed_languages) if contest.allowed_languages else ["python", "javascript", "cpp", "java"]

    return {
        "id": contest.id,
        "title": contest.title,
        "slug": contest.slug,
        "description": contest.description,
        "start_time": contest.start_time,
        "end_time": contest.end_time,
        "duration_minutes": contest.duration_minutes,
        "status": contest.status,
        "max_participants": contest.max_participants,
        "is_proctored": contest.is_proctored,
        "scoring_type": contest.scoring_type,
        "penalty_per_wrong_attempt_mins": contest.penalty_per_wrong_attempt_mins,
        "rules": contest.rules,
        "allowed_languages": allowed_langs,
        "problems_count": prob_count,
        "registered_count": reg_count,
        "is_registered": is_reg,
        "server_time": now,
        "time_to_start_seconds": time_to_start,
        "time_remaining_seconds": time_remaining,
    }


# ============================================================
# CONTEST REGISTRATION
# ============================================================

async def register_user_for_contest(
    db: AsyncSession,
    contest_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)

    if contest.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot register for a cancelled contest.")
    if contest.status == "ENDED":
        raise HTTPException(status_code=400, detail="Contest has already ended.")

    # Check already registered
    existing_reg = await db.execute(
        select(ContestRegistration).where(
            ContestRegistration.contest_id == contest.id,
            ContestRegistration.user_id == user_id,
        )
    )
    if existing_reg.scalar_one_or_none():
        return {"registered": True, "message": "Already registered for this contest."}

    # Check capacity limit
    if contest.max_participants:
        count_res = await db.execute(
            select(func.count()).select_from(ContestRegistration).where(ContestRegistration.contest_id == contest.id)
        )
        if (count_res.scalar() or 0) >= contest.max_participants:
            raise HTTPException(status_code=400, detail="Contest registration is full.")

    reg = ContestRegistration(
        contest_id=contest.id,
        user_id=user_id,
        registered_at=get_current_utc(),
        status="REGISTERED",
    )
    db.add(reg)

    # Initialize participant stats record
    stats = ContestParticipantStats(
        contest_id=contest.id,
        user_id=user_id,
        solved_count=0,
        total_score=0.0,
        penalty_minutes=0,
    )
    db.add(stats)

    await db.commit()
    return {"registered": True, "message": "Successfully registered for contest."}


# ============================================================
# CONTEST PROBLEM SET ACCESS
# ============================================================

async def get_contest_problems(
    db: AsyncSession,
    contest_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)
    now = get_current_utc()

    # Access control: problem set locked if contest is UPCOMING
    if contest.status == "UPCOMING":
        start = contest.start_time.replace(tzinfo=timezone.utc) if contest.start_time.tzinfo is None else contest.start_time
        remaining = max(0, int((start - now).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Contest has not started yet. Problems will be unlocked in {remaining} seconds.",
        )

    # Auto-register if LIVE and not yet registered
    existing_reg = await db.execute(
        select(ContestRegistration.id).where(
            ContestRegistration.contest_id == contest.id,
            ContestRegistration.user_id == user_id,
        )
    )
    if not existing_reg.first() and contest.status == "LIVE":
        await register_user_for_contest(db, contest.id, user_id)

    # Fetch contest problems joined with problem details
    stmt = (
        select(ContestProblem, CodingProblem)
        .join(CodingProblem, ContestProblem.problem_id == CodingProblem.id)
        .where(ContestProblem.contest_id == contest.id)
        .order_by(ContestProblem.order_index.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    # User's solved status & attempts per problem
    user_subs_stmt = select(ContestSubmission).where(
        ContestSubmission.contest_id == contest.id,
        ContestSubmission.user_id == user_id,
    )
    user_subs_res = await db.execute(user_subs_stmt)
    user_subs = user_subs_res.scalars().all()

    solved_probs: set[UUID] = set()
    attempt_counts: dict[UUID, int] = {}
    for s in user_subs:
        attempt_counts[s.problem_id] = attempt_counts.get(s.problem_id, 0) + 1
        if s.status == "Accepted":
            solved_probs.add(s.problem_id)

    problem_items: list[dict[str, Any]] = []
    for cp, p in rows:
        problem_items.append({
            "id": cp.id,
            "problem_id": p.id,
            "order_index": cp.order_index,
            "label": cp.label,
            "title": p.title,
            "slug": p.slug,
            "difficulty": p.difficulty,
            "topic": p.topic,
            "points": cp.points,
            "penalty_mins": cp.penalty_mins,
            "time_limit_seconds": cp.time_limit_seconds,
            "is_solved": p.id in solved_probs,
            "attempts_count": attempt_counts.get(p.id, 0),
        })

    end = contest.end_time.replace(tzinfo=timezone.utc) if contest.end_time.tzinfo is None else contest.end_time
    time_remaining = max(0, int((end - now).total_seconds())) if contest.status == "LIVE" else 0

    return {
        "contest_id": contest.id,
        "contest_title": contest.title,
        "status": contest.status,
        "server_time": now,
        "time_remaining_seconds": time_remaining,
        "problems": problem_items,
    }


async def get_contest_problem_detail(
    db: AsyncSession,
    contest_id: UUID,
    problem_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)
    now = get_current_utc()

    if contest.status == "UPCOMING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contest problems are locked until the contest starts.",
        )

    # Find the contest problem link
    stmt = (
        select(ContestProblem, CodingProblem)
        .join(CodingProblem, ContestProblem.problem_id == CodingProblem.id)
        .where(
            ContestProblem.contest_id == contest.id,
            or_(ContestProblem.problem_id == problem_id, CodingProblem.slug == str(problem_id)),
        )
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Problem not found in this contest.")

    cp, p = row
    p_detail = format_problem_detail(p)

    return {
        "id": cp.id,
        "problem_id": p.id,
        "order_index": cp.order_index,
        "label": cp.label,
        "points": cp.points,
        "penalty_mins": cp.penalty_mins,
        "time_limit_seconds": cp.time_limit_seconds,
        "title": p.title,
        "slug": p.slug,
        "description": p.description,
        "difficulty": p.difficulty,
        "topic": p.topic,
        "tags": p_detail.get("tags", []),
        "constraints": p_detail.get("constraints"),
        "input_format": p.input_format,
        "output_format": p.output_format,
        "examples": p_detail.get("examples", []),
        "starter_code": p_detail.get("starter_code", {}),
        "supported_languages": p_detail.get("supported_languages", ["python", "javascript", "cpp", "java"]),
        "test_cases": p_detail.get("test_cases", []),  # STRICTLY PUBLIC ONLY
    }


# ============================================================
# CONTEST CODE SUBMISSION & SCORING PIPELINE
# ============================================================

async def submit_contest_solution(
    db: AsyncSession,
    contest_id: UUID,
    problem_id: UUID,
    user_id: UUID,
    language: str,
    source_code: str,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)
    now = get_current_utc()

    # STRICT SERVER TIME VALIDATION
    if contest.status != "LIVE":
        if contest.status == "UPCOMING":
            raise HTTPException(status_code=400, detail="Contest has not started yet.")
        else:
            raise HTTPException(status_code=400, detail="Contest has ended. Submissions are closed.")

    # Find the contest problem
    cp_stmt = select(ContestProblem).where(
        ContestProblem.contest_id == contest.id,
        ContestProblem.problem_id == problem_id,
    )
    cp = (await db.execute(cp_stmt)).scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Problem is not part of this contest.")

    # Load problem with hidden test cases
    p_stmt = select(CodingProblem).where(CodingProblem.id == problem_id)
    problem = (await db.execute(p_stmt)).scalar_one()

    public_tests = json.loads(problem.test_cases) if problem.test_cases else []
    hidden_tests = json.loads(problem.hidden_test_cases) if problem.hidden_test_cases else []
    all_tests = public_tests + hidden_tests

    # Execute code in isolated sandbox
    exec_result = await execution_service.execute_test_cases(
        language=language,
        source_code=source_code,
        test_cases=all_tests,
    )

    sub_status = exec_result.get("status", "Runtime Error")
    passed_count = exec_result.get("total_passed", 0)
    total_count = exec_result.get("total_tests", len(all_tests))
    compile_err = exec_result.get("compile_error")
    runtime_err = exec_result.get("runtime_error")

    # Calculate execution time
    results_list = exec_result.get("results", [])
    total_exec_time = sum(r.get("execution_time", 0.0) for r in results_list)
    avg_exec_time = round(total_exec_time / max(1, len(results_list)), 2)

    # Calculate score percentage
    score_pct = round((passed_count / max(1, total_count)) * 100.0, 1)

    # 1. Record normal CodingSubmission (portfolio & history)
    coding_sub = CodingSubmission(
        user_id=user_id,
        problem_id=problem.id,
        language=language,
        source_code=source_code,
        status=sub_status,
        score=score_pct,
        passed_tests=passed_count,
        total_tests=total_count,
        execution_time=avg_exec_time,
        compile_error=compile_err,
        runtime_error=runtime_err,
        test_results=json.dumps(results_list[:5]),
        optimization_suggestions=json.dumps([]),
    )
    db.add(coding_sub)
    await db.flush()

    # 2. Check previous submissions for this problem by user in this contest
    prev_subs_stmt = (
        select(ContestSubmission)
        .where(
            ContestSubmission.contest_id == contest.id,
            ContestSubmission.problem_id == problem.id,
            ContestSubmission.user_id == user_id,
        )
        .order_by(ContestSubmission.submitted_at.asc())
    )
    prev_subs = (await db.execute(prev_subs_stmt)).scalars().all()
    already_solved = any(s.status == "Accepted" for s in prev_subs)

    # Points & penalty calculation
    points_awarded = 0
    penalty_minutes = 0
    start = contest.start_time.replace(tzinfo=timezone.utc) if contest.start_time.tzinfo is None else contest.start_time

    if sub_status == "Accepted" and not already_solved:
        points_awarded = cp.points
        # ICPC Formula: elapsed minutes from contest start + penalty for each previous wrong attempt
        elapsed_mins = max(0, int((now - start).total_seconds() / 60))
        wrong_attempts = len(prev_subs)
        penalty_minutes = elapsed_mins + (wrong_attempts * contest.penalty_per_wrong_attempt_mins)

    # 3. Record ContestSubmission
    contest_sub = ContestSubmission(
        contest_id=contest.id,
        problem_id=problem.id,
        user_id=user_id,
        coding_submission_id=coding_sub.id,
        language=language,
        source_code=source_code,
        submitted_at=now,
        status=sub_status,
        score=score_pct,
        execution_time=avg_exec_time,
        passed_tests=passed_count,
        total_tests=total_count,
        penalty_minutes=penalty_minutes,
    )
    db.add(contest_sub)
    await db.flush()

    # 4. Update ContestParticipantStats
    stats_stmt = select(ContestParticipantStats).where(
        ContestParticipantStats.contest_id == contest.id,
        ContestParticipantStats.user_id == user_id,
    )
    stats = (await db.execute(stats_stmt)).scalar_one_or_none()
    if not stats:
        stats = ContestParticipantStats(
            contest_id=contest.id,
            user_id=user_id,
            solved_count=0,
            total_score=0.0,
            penalty_minutes=0,
        )
        db.add(stats)

    # Update problems_data breakdown JSON
    p_data = json.loads(stats.problems_data) if stats.problems_data else {}
    pid_str = str(problem.id)
    cur_p = p_data.get(pid_str, {"label": cp.label, "solved": False, "attempts": 0, "points": 0})
    cur_p["attempts"] = cur_p.get("attempts", 0) + 1

    if sub_status == "Accepted" and not already_solved:
        cur_p["solved"] = True
        cur_p["points"] = cp.points
        cur_p["time_taken_mins"] = max(0, int((now - start).total_seconds() / 60))
        stats.solved_count += 1
        stats.total_score += cp.points
        stats.penalty_minutes += penalty_minutes

    p_data[pid_str] = cur_p
    stats.problems_data = json.dumps(p_data)
    stats.last_submission_at = now
    db.add(stats)
    await db.flush()

    # 5. Recalculate rankings for this contest
    await recalculate_contest_ranks(db, contest.id)
    await db.commit()

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        # Broadcast leaderboard update to all viewers
        await publish_event(
            WebSocketEventType.CONTEST_LEADERBOARD_UPDATED.value,
            {"contest_id": str(contest.id)},
            is_broadcast=True,
        )
        # Deliver submission feedback to the participant
        await publish_event(
            WebSocketEventType.CONTEST_PARTICIPANT_UPDATED.value,
            {
                "contest_id": str(contest.id),
                "submission_id": str(contest_sub.id),
                "status": sub_status,
                "current_rank": stats.rank,
                "total_score": stats.total_score,
            },
            user_id=user_id,
        )
    except Exception as ws_err:
        pass

    return {
        "submission_id": contest_sub.id,
        "status": sub_status,
        "score": score_pct,
        "points_awarded": points_awarded,
        "execution_time": avg_exec_time,
        "passed_tests": passed_count,
        "total_tests": total_count,
        "penalty_minutes": penalty_minutes,
        "current_rank": stats.rank,
        "total_solved": stats.solved_count,
        "total_score": stats.total_score,
        "compile_error": compile_err,
        "runtime_error": runtime_err,
    }


async def recalculate_contest_ranks(db: AsyncSession, contest_id: UUID) -> None:
    """Updates participant ranks using standard ICPC ordering: Score DESC, Penalty ASC, LastSubmission ASC."""
    stmt = (
        select(ContestParticipantStats)
        .where(ContestParticipantStats.contest_id == contest_id)
        .order_by(
            ContestParticipantStats.total_score.desc(),
            ContestParticipantStats.penalty_minutes.asc(),
            ContestParticipantStats.last_submission_at.asc(),
        )
    )
    all_stats = (await db.execute(stmt)).scalars().all()

    for idx, stat in enumerate(all_stats):
        stat.rank = idx + 1
        db.add(stat)


# ============================================================
# CONTEST LEADERBOARD & USER STATUS
# ============================================================

async def get_contest_leaderboard(
    db: AsyncSession,
    contest_id: UUID,
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)
    now = get_current_utc()

    # Recalculate ranks if needed
    await recalculate_contest_ranks(db, contest.id)

    # Fetch ranked stats with user details
    stmt = (
        select(ContestParticipantStats, User)
        .join(User, ContestParticipantStats.user_id == User.id)
        .where(ContestParticipantStats.contest_id == contest.id)
        .order_by(ContestParticipantStats.rank.asc())
    )
    rows = (await db.execute(stmt)).all()

    leaderboard_entries: list[dict[str, Any]] = []
    user_entry: dict[str, Any] | None = None

    for stat, user in rows:
        p_results = json.loads(stat.problems_data) if stat.problems_data else {}
        entry = {
            "rank": stat.rank or len(leaderboard_entries) + 1,
            "user_id": user.id,
            "username": user.email.split("@")[0] if user.email else "Anonymous",
            "full_name": user.full_name or user.email.split("@")[0],
            "solved_count": stat.solved_count,
            "total_score": stat.total_score,
            "penalty_minutes": stat.penalty_minutes,
            "last_submission_at": stat.last_submission_at,
            "problem_results": p_results,
        }
        leaderboard_entries.append(entry)

        if current_user_id and user.id == current_user_id:
            user_entry = entry

    # Fetch problem metadata for table columns
    probs_stmt = select(ContestProblem).where(ContestProblem.contest_id == contest.id).order_by(ContestProblem.order_index.asc())
    probs_res = (await db.execute(probs_stmt)).scalars().all()
    problem_metas = [{"problem_id": cp.problem_id, "label": cp.label, "points": cp.points} for cp in probs_res]

    return {
        "contest_id": contest.id,
        "contest_title": contest.title,
        "status": contest.status,
        "server_time": now,
        "total_participants": len(leaderboard_entries),
        "problems": problem_metas,
        "leaderboard": leaderboard_entries,
        "user_entry": user_entry,
    }


async def get_contest_user_status(
    db: AsyncSession,
    contest_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)

    # Check registration
    reg_stmt = select(ContestRegistration).where(
        ContestRegistration.contest_id == contest.id,
        ContestRegistration.user_id == user_id,
    )
    reg = (await db.execute(reg_stmt)).scalar_one_or_none()

    stats_stmt = select(ContestParticipantStats).where(
        ContestParticipantStats.contest_id == contest.id,
        ContestParticipantStats.user_id == user_id,
    )
    stats = (await db.execute(stats_stmt)).scalar_one_or_none()

    # Submissions
    subs_stmt = (
        select(ContestSubmission)
        .where(
            ContestSubmission.contest_id == contest.id,
            ContestSubmission.user_id == user_id,
        )
        .order_by(ContestSubmission.submitted_at.desc())
    )
    subs = (await db.execute(subs_stmt)).scalars().all()

    # Format problems performance
    problems_stmt = (
        select(ContestProblem, CodingProblem)
        .join(CodingProblem, ContestProblem.problem_id == CodingProblem.id)
        .where(ContestProblem.contest_id == contest.id)
        .order_by(ContestProblem.order_index.asc())
    )
    probs_rows = (await db.execute(problems_stmt)).all()

    p_data = json.loads(stats.problems_data) if stats and stats.problems_data else {}
    performance_list: list[dict[str, Any]] = []

    for cp, p in probs_rows:
        pid_str = str(p.id)
        info = p_data.get(pid_str, {})
        performance_list.append({
            "label": cp.label,
            "title": p.title,
            "points": cp.points,
            "solved": info.get("solved", False),
            "attempts": info.get("attempts", 0),
            "time_taken_mins": info.get("time_taken_mins"),
            "status": "Accepted" if info.get("solved") else ("Attempted" if info.get("attempts", 0) > 0 else "Unattempted"),
        })

    return {
        "contest_id": contest.id,
        "registered": reg is not None,
        "attended": len(subs) > 0,
        "solved_count": stats.solved_count if stats else 0,
        "total_score": stats.total_score if stats else 0.0,
        "penalty_minutes": stats.penalty_minutes if stats else 0,
        "rank": stats.rank if stats else None,
        "problems": performance_list,
        "submissions": [
            {
                "id": s.id,
                "problem_id": s.problem_id,
                "language": s.language,
                "status": s.status,
                "score": s.score,
                "execution_time": s.execution_time,
                "penalty_minutes": s.penalty_minutes,
                "submitted_at": s.submitted_at,
            }
            for s in subs
        ],
    }


async def get_contest_results(
    db: AsyncSession,
    contest_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    contest = await get_contest_by_id_or_slug(db, contest_id)

    # Leaderboard to calculate total participants and percentiles
    total_participants_res = await db.execute(
        select(func.count()).select_from(ContestParticipantStats).where(ContestParticipantStats.contest_id == contest.id)
    )
    total_participants = total_participants_res.scalar() or 0

    stats_stmt = select(ContestParticipantStats).where(
        ContestParticipantStats.contest_id == contest.id,
        ContestParticipantStats.user_id == user_id,
    )
    stats = (await db.execute(stats_stmt)).scalar_one_or_none()

    percentile = None
    if stats and stats.rank and total_participants > 1:
        percentile = round(((total_participants - stats.rank) / total_participants) * 100.0, 1)

    # Problem performance
    user_status = await get_contest_user_status(db, contest.id, user_id)

    return {
        "contest_id": contest.id,
        "contest_title": contest.title,
        "status": contest.status,
        "total_participants": total_participants,
        "final_rank": stats.rank if stats else None,
        "percentile": percentile,
        "total_score": stats.total_score if stats else 0.0,
        "solved_count": stats.solved_count if stats else 0,
        "penalty_minutes": stats.penalty_minutes if stats else 0,
        "problems": user_status.get("problems", []),
        "submissions": user_status.get("submissions", []),
    }


# ============================================================
# USER CONTEST HISTORY & ANALYTICS
# ============================================================

async def get_user_contest_history(
    db: AsyncSession,
    user_id: UUID,
) -> dict[str, Any]:
    stmt = (
        select(ContestParticipantStats, Contest)
        .join(Contest, ContestParticipantStats.contest_id == Contest.id)
        .where(ContestParticipantStats.user_id == user_id)
        .order_by(Contest.start_time.desc())
    )
    rows = (await db.execute(stmt)).all()

    items: list[dict[str, Any]] = []
    total_solved = 0
    ranks: list[int] = []

    for stat, contest in rows:
        total_p_res = await db.execute(
            select(func.count()).select_from(ContestParticipantStats).where(ContestParticipantStats.contest_id == contest.id)
        )
        total_p = total_p_res.scalar() or 1

        percentile = None
        if stat.rank and total_p > 1:
            percentile = round(((total_p - stat.rank) / total_p) * 100.0, 1)

        total_solved += stat.solved_count
        if stat.rank:
            ranks.append(stat.rank)

        items.append({
            "contest_id": contest.id,
            "contest_title": contest.title,
            "contest_slug": contest.slug,
            "start_time": contest.start_time,
            "end_time": contest.end_time,
            "status": contest.status,
            "rank": stat.rank,
            "total_participants": total_p,
            "solved_count": stat.solved_count,
            "total_score": stat.total_score,
            "penalty_minutes": stat.penalty_minutes,
            "percentile": percentile,
        })

    best_rank = min(ranks) if ranks else None
    avg_rank = round(sum(ranks) / len(ranks), 1) if ranks else None

    return {
        "contests": items,
        "total_contests": len(items),
        "best_rank": best_rank,
        "average_rank": avg_rank,
        "total_problems_solved": total_solved,
    }


# ============================================================
# ADMIN CONTEST ARCHITECTURE
# ============================================================

async def admin_create_contest(
    db: AsyncSession,
    payload: Any,
) -> Contest:
    title = payload.title.strip()
    slug = slugify(title)
    existing = await db.execute(select(Contest).where(Contest.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(get_current_utc().timestamp())}"

    end_time = payload.start_time + timedelta(minutes=payload.duration_minutes)

    contest = Contest(
        title=title,
        slug=slug,
        description=payload.description,
        start_time=payload.start_time,
        end_time=end_time,
        duration_minutes=payload.duration_minutes,
        status="UPCOMING",
        max_participants=payload.max_participants,
        is_proctored=payload.is_proctored,
        scoring_type=payload.scoring_type,
        penalty_per_wrong_attempt_mins=payload.penalty_per_wrong_attempt_mins,
        rules=payload.rules,
        allowed_languages=json.dumps(["python", "javascript", "cpp", "java"]),
    )
    db.add(contest)
    await db.flush()

    for idx, p in enumerate(payload.problems):
        cp = ContestProblem(
            contest_id=contest.id,
            problem_id=p.problem_id,
            order_index=p.order_index or (idx + 1),
            label=p.label or chr(65 + idx),
            points=p.points,
            penalty_mins=p.penalty_mins,
            time_limit_seconds=p.time_limit_seconds,
        )
        db.add(cp)

    await db.commit()
    return contest
