import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.model import User
from app.modules.coding.ai_review import (
    calculate_coding_score,
    generate_ai_code_review,
    generate_ai_coding_assistance,
)
from app.modules.coding.execution import execution_service
from app.modules.coding.model import CodingProblem, CodingSubmission

logger = logging.getLogger(__name__)


# ============================================================
# PROBLEM MANAGEMENT & ADVANCED RETRIEVAL (8B-4)
# ============================================================

async def get_coding_problems(
    db: AsyncSession,
    difficulty: str | None = None,
    topic: str | None = None,
    tag: str | None = None,
    company: str | None = None,
    role: str | None = None,
    search: str | None = None,
    solved: bool | None = None,
    attempted: bool | None = None,
    sort: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user_id: UUID | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    # Ensure initial seed problems exist
    await seed_initial_coding_problems(db)

    query = select(CodingProblem)

    # 1. Filter by difficulty
    if difficulty and difficulty.lower() != "all":
        query = query.where(func.lower(CodingProblem.difficulty) == difficulty.lower())

    # 2. Filter by topic
    if topic and topic.lower() != "all":
        query = query.where(func.lower(CodingProblem.topic) == topic.lower())

    # 3. Filter by tag
    if tag and tag.lower() != "all":
        pattern = f"%{tag.strip().lower()}%"
        query = query.where(
            func.lower(CodingProblem.tags).like(pattern)
            | func.lower(CodingProblem.topic).like(pattern)
        )

    # 4. Filter by company
    if company and company.lower() != "all":
        pattern = f"%{company.strip().lower()}%"
        query = query.where(func.lower(CodingProblem.company_tags).like(pattern))

    # 5. Filter by role
    if role and role.lower() != "all":
        pattern = f"%{role.strip().lower()}%"
        query = query.where(func.lower(CodingProblem.role_tags).like(pattern))

    # 6. Filter by search query
    if search and search.strip():
        search_pattern = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(CodingProblem.title).like(search_pattern)
            | func.lower(CodingProblem.description).like(search_pattern)
            | func.lower(CodingProblem.topic).like(search_pattern)
        )

    # 7. User-specific solved/attempted filtering
    solved_problem_ids: set[UUID] = set()
    attempted_problem_ids: set[UUID] = set()

    if current_user_id:
        user_subs_res = await db.execute(
            select(CodingSubmission.problem_id, CodingSubmission.status).where(
                CodingSubmission.user_id == current_user_id
            )
        )
        for p_id, p_status in user_subs_res.all():
            attempted_problem_ids.add(p_id)
            if p_status == "Accepted":
                solved_problem_ids.add(p_id)

        if solved is True:
            if not solved_problem_ids:
                return [], 0, 1
            query = query.where(CodingProblem.id.in_(solved_problem_ids))
        elif solved is False:
            if solved_problem_ids:
                query = query.where(CodingProblem.id.not_in(solved_problem_ids))

        if attempted is True:
            if not attempted_problem_ids:
                return [], 0, 1
            query = query.where(CodingProblem.id.in_(attempted_problem_ids))
        elif attempted is False:
            if attempted_problem_ids:
                query = query.where(CodingProblem.id.not_in(attempted_problem_ids))

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    # 8. Server-side Sorting
    diff_order = case(
        (func.lower(CodingProblem.difficulty) == "easy", 1),
        (func.lower(CodingProblem.difficulty) == "medium", 2),
        (func.lower(CodingProblem.difficulty) == "hard", 3),
        else_=4,
    )

    if sort == "newest":
        query = query.order_by(desc(CodingProblem.created_at))
    elif sort == "oldest":
        query = query.order_by(asc(CodingProblem.created_at))
    elif sort == "title_asc":
        query = query.order_by(asc(CodingProblem.title))
    elif sort == "title_desc":
        query = query.order_by(desc(CodingProblem.title))
    elif sort == "difficulty_asc":
        query = query.order_by(diff_order.asc(), asc(CodingProblem.title))
    elif sort == "difficulty_desc":
        query = query.order_by(diff_order.desc(), asc(CodingProblem.title))
    else:
        # Default order: Easy -> Medium -> Hard, then alphabetical
        query = query.order_by(diff_order.asc(), asc(CodingProblem.title))

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    problems = list(result.scalars().all())

    # 9. Query real acceptance rates across PostgreSQL submissions
    acceptance_map: dict[UUID, float] = {}
    if problems:
        problem_ids = [p.id for p in problems]
        acc_res = await db.execute(
            select(
                CodingSubmission.problem_id,
                func.count(CodingSubmission.id).label("total_cnt"),
                func.sum(case((CodingSubmission.status == "Accepted", 1), else_=0)).label("acc_cnt"),
            )
            .where(CodingSubmission.problem_id.in_(problem_ids))
            .group_by(CodingSubmission.problem_id)
        )
        for p_id, total_cnt, acc_cnt in acc_res.all():
            if total_cnt and total_cnt > 0:
                acc_rate = round((acc_cnt / total_cnt) * 100, 1)
                acceptance_map[p_id] = acc_rate

    # Format list items
    items = []
    for p in problems:
        langs = json.loads(p.supported_languages) if p.supported_languages else ["python", "javascript", "cpp", "java"]
        tags_list = json.loads(p.tags) if p.tags else []
        company_list = json.loads(p.company_tags) if p.company_tags else []
        role_list = json.loads(p.role_tags) if p.role_tags else []

        items.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "difficulty": p.difficulty,
            "topic": p.topic,
            "tags": tags_list,
            "company_tags": company_list,
            "role_tags": role_list,
            "supported_languages": langs,
            "is_solved": p.id in solved_problem_ids if current_user_id else None,
            "is_attempted": p.id in attempted_problem_ids if current_user_id else None,
            "acceptance_rate": acceptance_map.get(p.id, None),
            "created_at": p.created_at,
        })

    return items, total, total_pages


async def get_coding_problem_by_id_or_slug(db: AsyncSession, id_or_slug: str | UUID) -> CodingProblem:
    await seed_initial_coding_problems(db)

    problem: CodingProblem | None = None
    try:
        if isinstance(id_or_slug, UUID):
            val_uuid = id_or_slug
        else:
            val_uuid = UUID(str(id_or_slug))
        res = await db.execute(select(CodingProblem).where(CodingProblem.id == val_uuid))
        problem = res.scalar_one_or_none()
    except (ValueError, AttributeError):
        res = await db.execute(select(CodingProblem).where(CodingProblem.slug == str(id_or_slug)))
        problem = res.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coding problem '{id_or_slug}' not found.",
        )
    return problem


def format_problem_detail(problem: CodingProblem) -> dict[str, Any]:
    """Prepares problem details for candidate view, strictly excluding hidden test cases."""
    examples = json.loads(problem.examples) if problem.examples else []
    starter_code = json.loads(problem.starter_code) if problem.starter_code else {}
    supported_langs = json.loads(problem.supported_languages) if problem.supported_languages else ["python", "javascript", "cpp", "java"]
    sample_tests = json.loads(problem.test_cases) if problem.test_cases else []
    tags_list = json.loads(problem.tags) if problem.tags else []
    company_list = json.loads(problem.company_tags) if problem.company_tags else []
    role_list = json.loads(problem.role_tags) if problem.role_tags else []
    hints_list = json.loads(problem.hints) if problem.hints else []

    # Format constraints
    constraints_data = problem.constraints
    if constraints_data and constraints_data.startswith("["):
        try:
            constraints_data = json.loads(constraints_data)
        except Exception:
            pass

    return {
        "id": problem.id,
        "title": problem.title,
        "slug": problem.slug,
        "description": problem.description,
        "difficulty": problem.difficulty,
        "topic": problem.topic,
        "tags": tags_list,
        "company_tags": company_list,
        "role_tags": role_list,
        "constraints": constraints_data,
        "input_format": problem.input_format,
        "output_format": problem.output_format,
        "examples": examples,
        "starter_code": starter_code,
        "supported_languages": supported_langs,
        "sample_test_cases": sample_tests,
        "expected_time_complexity": problem.expected_time_complexity,
        "expected_space_complexity": problem.expected_space_complexity,
        "hints": hints_list,
        "created_at": problem.created_at,
    }



# ============================================================
# CODE RUN & SUBMISSION WORKFLOWS
# ============================================================

async def run_sample_code(
    db: AsyncSession,
    problem_id: UUID,
    language: str,
    source_code: str,
) -> dict[str, Any]:
    problem = await get_coding_problem_by_id_or_slug(db, problem_id)
    sample_tests = json.loads(problem.test_cases) if problem.test_cases else []

    if not sample_tests:
        # Fallback to examples if test_cases empty
        examples = json.loads(problem.examples) if problem.examples else []
        sample_tests = [{"input": ex["input"], "output": ex["output"]} for ex in examples]

    exec_result = await execution_service.execute_test_cases(
        language=language,
        source_code=source_code,
        test_cases=sample_tests,
        stop_on_first_failure=False,
    )
    return exec_result


async def submit_code(
    db: AsyncSession,
    user_id: UUID,
    problem_id: UUID,
    language: str,
    source_code: str,
    interview_id: UUID | None = None,
) -> CodingSubmission:
    problem = await get_coding_problem_by_id_or_slug(db, problem_id)

    sample_tests = json.loads(problem.test_cases) if problem.test_cases else []
    hidden_tests = json.loads(problem.hidden_test_cases) if problem.hidden_test_cases else []

    full_suite = sample_tests + hidden_tests
    if not full_suite:
        examples = json.loads(problem.examples) if problem.examples else []
        full_suite = [{"input": ex["input"], "output": ex["output"]} for ex in examples]

    # Execute all test cases
    exec_result = await execution_service.execute_test_cases(
        language=language,
        source_code=source_code,
        test_cases=full_suite,
        stop_on_first_failure=False,
    )

    passed_count = exec_result["total_passed"]
    total_count = exec_result["total_tests"]
    status_str = exec_result["status"]

    # Calculate average runtime
    times = [r["execution_time"] for r in exec_result["results"] if r.get("execution_time") is not None]
    avg_runtime = sum(times) / len(times) if times else 0.0

    # Deterministic score calculation
    score = calculate_coding_score(
        passed_tests=passed_count,
        total_tests=total_count,
        avg_runtime_ms=avg_runtime,
        status=status_str,
        code_length=len(source_code),
    )

    # AI Code Review
    ai_review_dict = await generate_ai_code_review(
        problem_title=problem.title,
        language=language,
        source_code=source_code,
        status=status_str,
        passed_tests=passed_count,
        total_tests=total_count,
    )

    comp_time = ai_review_dict.get("complexity", {}).get("time", "O(n)")
    comp_space = ai_review_dict.get("complexity", {}).get("space", "O(1)")
    suggestions = ai_review_dict.get("optimization_suggestions", [])

    # Store submission
    # Redact input/output from hidden tests in saved test_results for security
    sanitized_results = []
    for idx, r in enumerate(exec_result["results"]):
        is_sample = idx < len(sample_tests)
        sanitized_results.append({
            "test_index": r["test_index"],
            "passed": r["passed"],
            "execution_time": r["execution_time"],
            "error": r["error"],
            # Show input/output only for public sample tests
            "input": r["input"] if is_sample else "[Hidden Test]",
            "expected_output": r["expected_output"] if is_sample else "[Hidden Test]",
            "actual_output": r["actual_output"] if is_sample else ("[Passed]" if r["passed"] else "[Mismatch]"),
        })

    submission = CodingSubmission(
        user_id=user_id,
        problem_id=problem.id,
        interview_id=interview_id,
        language=language,
        source_code=source_code,
        status=status_str,
        score=score,
        passed_tests=passed_count,
        total_tests=total_count,
        execution_time=round(avg_runtime, 2),
        compile_error=exec_result.get("compile_error"),
        runtime_error=exec_result.get("runtime_error"),
        test_results=json.dumps(sanitized_results),
        complexity_time=comp_time,
        complexity_space=comp_space,
        ai_review=json.dumps(ai_review_dict),
        optimization_suggestions=json.dumps(suggestions),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Sync personalized learning skill performance
    try:
        from app.modules.learning.evaluator import sync_and_persist_skill_performances
        await sync_and_persist_skill_performances(db, user_id)
    except Exception as e:
        logger.warning(f"Failed to auto-update skill performance on coding submission: {e}")

    return submission


# ============================================================
# SUBMISSIONS & STATS
# ============================================================

async def get_user_submissions(
    db: AsyncSession,
    user_id: UUID,
    problem_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    query = (
        select(CodingSubmission, CodingProblem.title.label("problem_title"))
        .join(CodingProblem, CodingSubmission.problem_id == CodingProblem.id)
        .where(CodingSubmission.user_id == user_id)
    )

    if problem_id:
        query = query.where(CodingSubmission.problem_id == problem_id)

    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    query = query.order_by(desc(CodingSubmission.created_at))
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = (await db.execute(query)).all()
    results = []
    for sub, prob_title in rows:
        results.append(format_submission_response(sub, prob_title))

    return results, total


async def get_submission_by_id(db: AsyncSession, submission_id: UUID, user_id: UUID) -> dict[str, Any]:
    row = (
        await db.execute(
            select(CodingSubmission, CodingProblem.title.label("problem_title"))
            .join(CodingProblem, CodingSubmission.problem_id == CodingProblem.id)
            .where(CodingSubmission.id == submission_id)
        )
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    sub, prob_title = row
    if sub.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this submission.",
        )

    return format_submission_response(sub, prob_title)


async def run_custom_code(
    db: AsyncSession,
    problem_id: UUID,
    language: str,
    source_code: str,
    custom_input: str,
) -> dict[str, Any]:
    await get_coding_problem_by_id_or_slug(db, problem_id)
    return await execution_service.execute_custom_input(
        language=language,
        source_code=source_code,
        custom_input=custom_input,
    )


async def get_ai_assistance(
    db: AsyncSession,
    problem_id: UUID,
    language: str,
    source_code: str,
    action: str,
    hint_level: int = 1,
    error_message: str | None = None,
) -> dict[str, Any]:
    problem = await get_coding_problem_by_id_or_slug(db, problem_id)
    stored_hints = json.loads(problem.hints) if problem.hints else []

    return await generate_ai_coding_assistance(
        problem_title=problem.title,
        problem_description=problem.description,
        language=language,
        source_code=source_code,
        action=action,
        hint_level=hint_level,
        error_message=error_message,
        stored_hints=stored_hints,
    )


async def get_user_coding_stats(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    res = await db.execute(
        select(CodingSubmission)
        .where(CodingSubmission.user_id == user_id)
        .order_by(desc(CodingSubmission.created_at))
    )
    submissions = list(res.scalars().all())

    if not submissions:
        return {
            "total_attempted": 0,
            "total_solved": 0,
            "success_rate": 0.0,
            "average_score": 0.0,
            "easy_solved": 0,
            "medium_solved": 0,
            "hard_solved": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "recent_submissions": [],
            "topic_breakdown": {},
        }

    attempted_problems = {sub.problem_id for sub in submissions}
    solved_problems = {sub.problem_id for sub in submissions if sub.status == "Accepted"}

    avg_score = sum(sub.score for sub in submissions) / len(submissions)
    success_rate = (len(solved_problems) / len(attempted_problems) * 100) if attempted_problems else 0.0

    # Difficulty & Topic breakdowns
    problem_topics: dict[str, int] = {}
    easy_solved = 0
    medium_solved = 0
    hard_solved = 0

    if solved_problems:
        prob_res = await db.execute(
            select(CodingProblem.id, CodingProblem.topic, CodingProblem.difficulty).where(
                CodingProblem.id.in_(solved_problems)
            )
        )
        for p_id, p_topic, p_diff in prob_res.all():
            problem_topics[p_topic] = problem_topics.get(p_topic, 0) + 1
            if p_diff.lower() == "easy":
                easy_solved += 1
            elif p_diff.lower() == "medium":
                medium_solved += 1
            elif p_diff.lower() == "hard":
                hard_solved += 1

    # Daily streak calculation
    acc_dates = sorted({sub.created_at.date() for sub in submissions if sub.status == "Accepted"}, reverse=True)
    current_streak = 0
    longest_streak = 0

    if acc_dates:
        today = datetime.now(timezone.utc).date()
        if acc_dates[0] in (today, today - timedelta(days=1)):
            expected = acc_dates[0]
            for d in acc_dates:
                if d == expected:
                    current_streak += 1
                    expected = d - timedelta(days=1)
                else:
                    break

        sorted_asc = sorted(acc_dates)
        temp_streak = 1
        longest_streak = 1
        for i in range(1, len(sorted_asc)):
            if sorted_asc[i] == sorted_asc[i - 1] + timedelta(days=1):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1

    # Format recent 5
    recent_formatted = []
    for sub in submissions[:5]:
        prob_res = await db.execute(select(CodingProblem.title).where(CodingProblem.id == sub.problem_id))
        prob_title = prob_res.scalar_one_or_none()
        recent_formatted.append(format_submission_response(sub, prob_title or "Coding Problem"))

    return {
        "total_attempted": len(attempted_problems),
        "total_solved": len(solved_problems),
        "success_rate": round(success_rate, 1),
        "average_score": round(avg_score, 1),
        "easy_solved": easy_solved,
        "medium_solved": medium_solved,
        "hard_solved": hard_solved,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "recent_submissions": recent_formatted,
        "topic_breakdown": problem_topics,
    }


async def get_leaderboard(
    db: AsyncSession,
    limit: int = 50,
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    users_stmt = (
        select(User.id, User.full_name, User.email)
        .join(CodingSubmission, User.id == CodingSubmission.user_id)
        .distinct()
    )
    users_res = await db.execute(users_stmt)
    candidate_users = users_res.all()

    leaderboard_entries = []
    for u_id, u_name, u_email in candidate_users:
        subs_res = await db.execute(
            select(CodingSubmission).where(CodingSubmission.user_id == u_id)
        )
        subs = list(subs_res.scalars().all())
        solved_ids = {s.problem_id for s in subs if s.status == "Accepted"}
        total_accepted = sum(1 for s in subs if s.status == "Accepted")
        avg_score = (sum(s.score for s in subs) / len(subs)) if subs else 0.0

        # Streak calculation
        acc_dates = sorted({s.created_at.date() for s in subs if s.status == "Accepted"}, reverse=True)
        streak = 0
        if acc_dates:
            today = datetime.now(timezone.utc).date()
            if acc_dates[0] in (today, today - timedelta(days=1)):
                expected = acc_dates[0]
                for d in acc_dates:
                    if d == expected:
                        streak += 1
                        expected = d - timedelta(days=1)
                    else:
                        break

        # Coding XP
        xp = (len(solved_ids) * 100) + int(avg_score * 5)
        display_name = u_name.strip() if u_name and u_name.strip() else (u_email.split("@")[0] if u_email else "Candidate")

        leaderboard_entries.append({
            "user_id": u_id,
            "user_name": display_name,
            "problems_solved": len(solved_ids),
            "total_accepted": total_accepted,
            "coding_xp": xp,
            "average_score": round(avg_score, 1),
            "current_streak": streak,
        })

    # Rank sorted by problems_solved DESC, coding_xp DESC, avg_score DESC
    leaderboard_entries.sort(key=lambda x: (x["problems_solved"], x["coding_xp"], x["average_score"]), reverse=True)

    user_rank = None
    ranked_list = []
    for idx, entry in enumerate(leaderboard_entries):
        rank = idx + 1
        item = {
            "rank": rank,
            **entry
        }
        ranked_list.append(item)
        if current_user_id and entry["user_id"] == current_user_id:
            user_rank = rank

    return {
        "leaderboard": ranked_list[:limit],
        "total_candidates": len(ranked_list),
        "user_rank": user_rank,
    }


async def get_personalized_recommendations(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    subs_res = await db.execute(
        select(CodingSubmission.problem_id, CodingSubmission.status).where(CodingSubmission.user_id == user_id)
    )
    user_subs = subs_res.all()
    solved_ids = {p_id for p_id, status_val in user_subs if status_val == "Accepted"}
    attempted_ids = {p_id for p_id, _ in user_subs}

    all_probs_res = await db.execute(select(CodingProblem))
    all_probs = list(all_probs_res.scalars().all())

    topic_stats: dict[str, dict[str, int]] = {}
    for p in all_probs:
        t = p.topic
        if t not in topic_stats:
            topic_stats[t] = {"total": 0, "solved": 0, "failed": 0}
        topic_stats[t]["total"] += 1
        if p.id in solved_ids:
            topic_stats[t]["solved"] += 1
        elif p.id in attempted_ids:
            topic_stats[t]["failed"] += 1

    weak_topics: list[str] = []
    strong_topics: list[str] = []
    reasons: list[str] = []

    for t, st in topic_stats.items():
        if st["solved"] >= 1 and st["failed"] == 0:
            strong_topics.append(t)
        elif st["failed"] > 0 or st["solved"] == 0:
            weak_topics.append(t)

    unsolved = [p for p in all_probs if p.id not in solved_ids]
    recommended: list[CodingProblem] = []

    for p in unsolved:
        if p.topic in weak_topics:
            recommended.append(p)
            reasons.append(f"Strengthen your skills in {p.topic} with this challenge.")
        if len(recommended) >= 5:
            break

    if len(recommended) < 5:
        for p in unsolved:
            if p not in recommended:
                recommended.append(p)
                reasons.append("Explore new algorithmic patterns to expand your coding versatility.")
            if len(recommended) >= 5:
                break

    rec_items = []
    for p in recommended:
        langs = json.loads(p.supported_languages) if p.supported_languages else ["python", "javascript", "cpp", "java"]
        rec_items.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "difficulty": p.difficulty,
            "topic": p.topic,
            "tags": json.loads(p.tags) if p.tags else [],
            "company_tags": json.loads(p.company_tags) if p.company_tags else [],
            "role_tags": json.loads(p.role_tags) if p.role_tags else [],
            "supported_languages": langs,
            "is_solved": False,
            "is_attempted": p.id in attempted_ids,
            "acceptance_rate": None,
            "created_at": p.created_at,
        })

    return {
        "weak_topics": weak_topics[:5],
        "strong_topics": strong_topics[:5],
        "recommended_problems": rec_items,
        "recommendation_reasons": reasons[:len(rec_items)],
    }



def format_submission_response(sub: CodingSubmission, problem_title: str | None = None) -> dict[str, Any]:
    test_results = json.loads(sub.test_results) if sub.test_results else []
    ai_review = json.loads(sub.ai_review) if sub.ai_review else None
    opt_suggestions = json.loads(sub.optimization_suggestions) if sub.optimization_suggestions else []

    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "problem_id": sub.problem_id,
        "problem_title": problem_title,
        "interview_id": sub.interview_id,
        "language": sub.language,
        "source_code": sub.source_code,
        "status": sub.status,
        "score": sub.score,
        "passed_tests": sub.passed_tests,
        "total_tests": sub.total_tests,
        "execution_time": sub.execution_time,
        "compile_error": sub.compile_error,
        "runtime_error": sub.runtime_error,
        "test_results": test_results,
        "complexity_time": sub.complexity_time,
        "complexity_space": sub.complexity_space,
        "ai_review": ai_review,
        "optimization_suggestions": opt_suggestions,
        "created_at": sub.created_at,
    }


# ============================================================
# CANONICAL SEED PROBLEMS
# ============================================================

INITIAL_PROBLEMS = [
    {
        "title": "Two Sum",
        "slug": "two-sum",
        "difficulty": "Easy",
        "topic": "Arrays & Hashing",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\\n\\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.\\n\\nPrint the two 0-based indices separated by a single space.",
        "constraints": json.dumps([
            "2 <= nums.length <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "Only one valid answer exists."
        ]),
        "input_format": "Line 1: space-separated integers representing the array nums\\nLine 2: single integer representing the target",
        "output_format": "Space-separated indices (e.g. '0 1')",
        "examples": json.dumps([
            {"input": "2 7 11 15\\n9", "output": "0 1", "explanation": "nums[0] + nums[1] == 9, so we return 0 1."},
            {"input": "3 2 4\\n6", "output": "1 2", "explanation": "nums[1] + nums[2] == 6, so we return 1 2."},
            {"input": "3 3\\n6", "output": "0 1", "explanation": "nums[0] + nums[1] == 6, so we return 0 1."}
        ]),
        "starter_code": json.dumps({
            "python": """import sys

def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []

if __name__ == "__main__":
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) >= 2:
        nums = list(map(int, lines[0].split()))
        target = int(lines[1].strip())
        res = two_sum(nums, target)
        print(f"{res[0]} {res[1]}")
""",
            "javascript": """const fs = require('fs');

function twoSum(nums, target) {
    const map = new Map();
    for (let i = 0; i < nums.length; i++) {
        const diff = target - nums[i];
        if (map.has(diff)) {
            return [map.get(diff), i];
        }
        map.set(nums[i], i);
    }
    return [];
}

const lines = fs.readFileSync(0, 'utf-8').trim().split('\\n');
if (lines.length >= 2) {
    const nums = lines[0].trim().split(/\\s+/).map(Number);
    const target = Number(lines[1].trim());
    const res = twoSum(nums, target);
    console.log(`${res[0]} ${res[1]}`);
}
""",
            "cpp": """#include <iostream>
#include <vector>
#include <unordered_map>
#include <sstream>

std::vector<int> twoSum(const std::vector<int>& nums, int target) {
    std::unordered_map<int, int> seen;
    for (int i = 0; i < (int)nums.size(); ++i) {
        int diff = target - nums[i];
        if (seen.count(diff)) return {seen[diff], i};
        seen[nums[i]] = i;
    }
    return {};
}

int main() {
    std::string line;
    if (std::getline(std::cin, line)) {
        std::stringstream ss(line);
        int val;
        std::vector<int> nums;
        while (ss >> val) nums.push_back(val);
        int target;
        if (std::cin >> target) {
            auto res = twoSum(nums, target);
            if (res.size() == 2) {
                std::cout << res[0] << " " << res[1] << std::endl;
            }
        }
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int diff = target - nums[i];
            if (map.containsKey(diff)) {
                return new int[] { map.get(diff), i };
            }
            map.put(nums[i], i);
        }
        return new int[]{};
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (sc.hasNextLine()) {
            String[] parts = sc.nextLine().trim().split("\\\\s+");
            int[] nums = new int[parts.length];
            for (int i = 0; i < parts.length; i++) {
                nums[i] = Integer.parseInt(parts[i]);
            }
            if (sc.hasNextInt()) {
                int target = sc.nextInt();
                int[] res = twoSum(nums, target);
                if (res.length == 2) {
                    System.out.println(res[0] + " " + res[1]);
                }
            }
        }
    }
}
"""
        }),
        "supported_languages": json.dumps(["python", "javascript", "cpp", "java"]),
        "test_cases": json.dumps([
            {"input": "2 7 11 15\n9", "output": "0 1"},
            {"input": "3 2 4\n6", "output": "1 2"},
            {"input": "3 3\n6", "output": "0 1"}
        ]),
        "hidden_test_cases": json.dumps([
            {"input": "1 5 8 10 14\n19", "output": "1 4"},
            {"input": "-3 4 3 90\n0", "output": "0 2"},
            {"input": "1000 2000 3000 4000\n7000", "output": "2 3"},
            {"input": "0 4 3 0\n0", "output": "0 3"}
        ])
    },
    {
        "title": "Valid Palindrome",
        "slug": "valid-palindrome",
        "difficulty": "Easy",
        "topic": "Two Pointers",
        "description": "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.\\n\\nPrint 'true' if the given phrase is a palindrome, or 'false' otherwise.",
        "constraints": json.dumps([
            "1 <= s.length <= 2 * 10^5",
            "s consists only of printable ASCII characters."
        ]),
        "input_format": "A single line containing the string s",
        "output_format": "'true' or 'false'",
        "examples": json.dumps([
            {"input": "A man, a plan, a canal: Panama", "output": "true", "explanation": "'amanaplanacanalpanama' is a palindrome."},
            {"input": "race a car", "output": "false", "explanation": "'raceacar' is not a palindrome."},
            {"input": " ", "output": "true", "explanation": "An empty string reads the same forward and backward."}
        ]),
        "starter_code": json.dumps({
            "python": """import sys

def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]

if __name__ == "__main__":
    line = sys.stdin.read().rstrip('\\r\\n')
    print("true" if is_palindrome(line) else "false")
""",
            "javascript": """const fs = require('fs');

function isPalindrome(s) {
    const cleaned = s.toLowerCase().replace(/[^a-z0-9]/g, '');
    const rev = cleaned.split('').reverse().join('');
    return cleaned === rev;
}

const input = fs.readFileSync(0, 'utf-8').replace(/[\\r\\n]+$/, '');
console.log(isPalindrome(input) ? "true" : "false");
""",
            "cpp": """#include <iostream>
#include <string>
#include <cctype>

bool isPalindrome(const std::string& s) {
    int l = 0, r = (int)s.size() - 1;
    while (l < r) {
        while (l < r && !std::isalnum(s[l])) l++;
        while (l < r && !std::isalnum(s[r])) r--;
        if (std::tolower(s[l]) != std::tolower(s[r])) return false;
        l++; r--;
    }
    return true;
}

int main() {
    std::string line;
    if (std::getline(std::cin, line)) {
        std::cout << (isPalindrome(line) ? "true" : "false") << std::endl;
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static boolean isPalindrome(String s) {
        int l = 0, r = s.length() - 1;
        while (l < r) {
            while (l < r && !Character.isLetterOrDigit(s.charAt(l))) l++;
            while (l < r && !Character.isLetterOrDigit(s.charAt(r))) r--;
            if (Character.toLowerCase(s.charAt(l)) != Character.toLowerCase(s.charAt(r))) {
                return false;
            }
            l++; r--;
        }
        return true;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String line = sc.hasNextLine() ? sc.nextLine() : "";
        System.out.println(isPalindrome(line) ? "true" : "false");
    }
}
"""
        }),
        "supported_languages": json.dumps(["python", "javascript", "cpp", "java"]),
        "test_cases": json.dumps([
            {"input": "A man, a plan, a canal: Panama", "output": "true"},
            {"input": "race a car", "output": "false"},
            {"input": " ", "output": "true"}
        ]),
        "hidden_test_cases": json.dumps([
            {"input": "0P", "output": "false"},
            {"input": "ab_a", "output": "true"},
            {"input": "Was it a car or a cat I saw?", "output": "true"},
            {"input": "Madam, in Eden, I'm Adam", "output": "true"}
        ])
    },
    {
        "title": "Maximum Subarray",
        "slug": "maximum-subarray",
        "difficulty": "Medium",
        "topic": "Dynamic Programming",
        "description": "Given an integer array nums, find the contiguous subarray (containing at least one number) which has the largest sum and print its sum.",
        "constraints": json.dumps([
            "1 <= nums.length <= 10^5",
            "-10^4 <= nums[i] <= 10^4"
        ]),
        "input_format": "A single line of space-separated integers representing nums",
        "output_format": "A single integer denoting the maximum subarray sum",
        "examples": json.dumps([
            {"input": "-2 1 -3 4 -1 2 1 -5 4", "output": "6", "explanation": "The subarray [4,-1,2,1] has the largest sum 6."},
            {"input": "1", "output": "1", "explanation": "The subarray [1] has the largest sum 1."},
            {"input": "5 4 -1 7 8", "output": "23", "explanation": "The subarray [5,4,-1,7,8] has the largest sum 23."}
        ]),
        "starter_code": json.dumps({
            "python": """import sys

def max_sub_array(nums):
    max_sum = current_sum = nums[0]
    for x in nums[1:]:
        current_sum = max(x, current_sum + x)
        max_sum = max(max_sum, current_sum)
    return max_sum

if __name__ == "__main__":
    line = sys.stdin.read().strip()
    if line:
        nums = list(map(int, line.split()))
        print(max_sub_array(nums))
""",
            "javascript": """const fs = require('fs');

function maxSubArray(nums) {
    let maxSum = nums[0];
    let currentSum = nums[0];
    for (let i = 1; i < nums.length; i++) {
        currentSum = Math.max(nums[i], currentSum + nums[i]);
        maxSum = Math.max(maxSum, currentSum);
    }
    return maxSum;
}

const input = fs.readFileSync(0, 'utf-8').trim();
if (input) {
    const nums = input.split(/\\s+/).map(Number);
    console.log(maxSubArray(nums));
}
""",
            "cpp": """#include <iostream>
#include <vector>
#include <algorithm>
#include <sstream>

int maxSubArray(const std::vector<int>& nums) {
    int maxSum = nums[0];
    int currentSum = nums[0];
    for (size_t i = 1; i < nums.size(); ++i) {
        currentSum = std::max(nums[i], currentSum + nums[i]);
        maxSum = std::max(maxSum, currentSum);
    }
    return maxSum;
}

int main() {
    std::string line;
    if (std::getline(std::cin, line)) {
        std::stringstream ss(line);
        int val;
        std::vector<int> nums;
        while (ss >> val) nums.push_back(val);
        if (!nums.empty()) {
            std::cout << maxSubArray(nums) << std::endl;
        }
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static int maxSubArray(int[] nums) {
        int maxSum = nums[0];
        int currentSum = nums[0];
        for (int i = 1; i < nums.length; i++) {
            currentSum = Math.max(nums[i], currentSum + nums[i]);
            maxSum = Math.max(maxSum, currentSum);
        }
        return maxSum;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (sc.hasNextLine()) {
            String[] parts = sc.nextLine().trim().split("\\\\s+");
            int[] nums = new int[parts.length];
            for (int i = 0; i < parts.length; i++) {
                nums[i] = Integer.parseInt(parts[i]);
            }
            System.out.println(maxSubArray(nums));
        }
    }
}
"""
        }),
        "supported_languages": json.dumps(["python", "javascript", "cpp", "java"]),
        "test_cases": json.dumps([
            {"input": "-2 1 -3 4 -1 2 1 -5 4", "output": "6"},
            {"input": "1", "output": "1"},
            {"input": "5 4 -1 7 8", "output": "23"}
        ]),
        "hidden_test_cases": json.dumps([
            {"input": "-1", "output": "-1"},
            {"input": "-5 -2 -8 -1", "output": "-1"},
            {"input": "1 2 3 4 5", "output": "15"},
            {"input": "-2 -1", "output": "-1"}
        ])
    },
    {
        "title": "Binary Search",
        "slug": "binary-search",
        "difficulty": "Easy",
        "topic": "Binary Search",
        "description": "Given an array of integers nums which is sorted in ascending order, and an integer target, write a function to search target in nums. If target exists, then print its 0-based index. Otherwise, print -1.",
        "constraints": json.dumps([
            "1 <= nums.length <= 10^4",
            "-10^4 < nums[i], target < 10^4",
            "All the integers in nums are unique.",
            "nums is sorted in ascending order."
        ]),
        "input_format": "Line 1: space-separated sorted integers representing nums\\nLine 2: single integer representing target",
        "output_format": "A single integer denoting the index or -1",
        "examples": json.dumps([
            {"input": "-1 0 3 5 9 12\\n9", "output": "4", "explanation": "9 exists in nums and its index is 4."},
            {"input": "-1 0 3 5 9 12\\n2", "output": "-1", "explanation": "2 does not exist in nums so return -1."}
        ]),
        "starter_code": json.dumps({
            "python": """import sys

def binary_search(nums, target):
    low, high = 0, len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1

if __name__ == "__main__":
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) >= 2:
        nums = list(map(int, lines[0].split()))
        target = int(lines[1].strip())
        print(binary_search(nums, target))
""",
            "javascript": """const fs = require('fs');

function binarySearch(nums, target) {
    let low = 0, high = nums.length - 1;
    while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        if (nums[mid] === target) return mid;
        if (nums[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}

const lines = fs.readFileSync(0, 'utf-8').trim().split('\\n');
if (lines.length >= 2) {
    const nums = lines[0].trim().split(/\\s+/).map(Number);
    const target = Number(lines[1].trim());
    console.log(binarySearch(nums, target));
}
""",
            "cpp": """#include <iostream>
#include <vector>
#include <sstream>

int binarySearch(const std::vector<int>& nums, int target) {
    int low = 0, high = (int)nums.size() - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (nums[mid] == target) return mid;
        if (nums[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}

int main() {
    std::string line;
    if (std::getline(std::cin, line)) {
        std::stringstream ss(line);
        int val;
        std::vector<int> nums;
        while (ss >> val) nums.push_back(val);
        int target;
        if (std::cin >> target) {
            std::cout << binarySearch(nums, target) << std::endl;
        }
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static int search(int[] nums, int target) {
        int low = 0, high = nums.length - 1;
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (nums[mid] == target) return mid;
            if (nums[mid] < target) low = mid + 1;
            else high = mid - 1;
        }
        return -1;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (sc.hasNextLine()) {
            String[] parts = sc.nextLine().trim().split("\\\\s+");
            int[] nums = new int[parts.length];
            for (int i = 0; i < parts.length; i++) {
                nums[i] = Integer.parseInt(parts[i]);
            }
            if (sc.hasNextInt()) {
                int target = sc.nextInt();
                System.out.println(search(nums, target));
            }
        }
    }
}
"""
        }),
        "supported_languages": json.dumps(["python", "javascript", "cpp", "java"]),
        "test_cases": json.dumps([
            {"input": "-1 0 3 5 9 12\n9", "output": "4"},
            {"input": "-1 0 3 5 9 12\n2", "output": "-1"}
        ]),
        "hidden_test_cases": json.dumps([
            {"input": "5\n5", "output": "0"},
            {"input": "2 5\n0", "output": "-1"},
            {"input": "1 3 5 7 9 11 13 15\n11", "output": "5"},
            {"input": "1 3 5 7 9 11 13 15\n16", "output": "-1"}
        ])
    },
    {
        "title": "Longest Substring Without Repeating Characters",
        "slug": "longest-substring-without-repeating-characters",
        "difficulty": "Medium",
        "topic": "Sliding Window",
        "description": "Given a string s, find the length of the longest substring without duplicate characters.",
        "constraints": json.dumps([
            "0 <= s.length <= 5 * 10^4",
            "s consists of English letters, digits, symbols and spaces."
        ]),
        "input_format": "A single line containing string s",
        "output_format": "A single integer denoting length of longest substring without duplicates",
        "examples": json.dumps([
            {"input": "abcabcbb", "output": "3", "explanation": "The answer is 'abc', with the length of 3."},
            {"input": "bbbbb", "output": "1", "explanation": "The answer is 'b', with the length of 1."},
            {"input": "pwwkew", "output": "3", "explanation": "The answer is 'wke', with the length of 3."}
        ]),
        "starter_code": json.dumps({
            "python": """import sys

def length_of_longest_substring(s):
    seen = {}
    max_len = 0
    start = 0
    for idx, ch in enumerate(s):
        if ch in seen and seen[ch] >= start:
            start = seen[ch] + 1
        seen[ch] = idx
        max_len = max(max_len, idx - start + 1)
    return max_len

if __name__ == "__main__":
    line = sys.stdin.read().rstrip('\\r\\n')
    print(length_of_longest_substring(line))
""",
            "javascript": """const fs = require('fs');

function lengthOfLongestSubstring(s) {
    const seen = new Map();
    let maxLen = 0, start = 0;
    for (let i = 0; i < s.length; i++) {
        const ch = s[i];
        if (seen.has(ch) && seen.get(ch) >= start) {
            start = seen.get(ch) + 1;
        }
        seen.set(ch, i);
        maxLen = Math.max(maxLen, i - start + 1);
    }
    return maxLen;
}

const input = fs.readFileSync(0, 'utf-8').replace(/[\\r\\n]+$/, '');
console.log(lengthOfLongestSubstring(input));
""",
            "cpp": """#include <iostream>
#include <string>
#include <unordered_map>
#include <algorithm>

int lengthOfLongestSubstring(const std::string& s) {
    std::unordered_map<char, int> seen;
    int maxLen = 0, start = 0;
    for (int i = 0; i < (int)s.size(); ++i) {
        char ch = s[i];
        if (seen.count(ch) && seen[ch] >= start) {
            start = seen[ch] + 1;
        }
        seen[ch] = i;
        maxLen = std::max(maxLen, i - start + 1);
    }
    return maxLen;
}

int main() {
    std::string line;
    if (std::getline(std::cin, line)) {
        std::cout << lengthOfLongestSubstring(line) << std::endl;
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static int lengthOfLongestSubstring(String s) {
        Map<Character, Integer> seen = new HashMap<>();
        int maxLen = 0, start = 0;
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (seen.containsKey(ch) && seen.get(ch) >= start) {
                start = seen.get(ch) + 1;
            }
            seen.put(ch, i);
            maxLen = Math.max(maxLen, i - start + 1);
        }
        return maxLen;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String line = sc.hasNextLine() ? sc.nextLine() : "";
        System.out.println(lengthOfLongestSubstring(line));
    }
}
"""
        }),
        "supported_languages": json.dumps(["python", "javascript", "cpp", "java"]),
        "test_cases": json.dumps([
            {"input": "abcabcbb", "output": "3"},
            {"input": "bbbbb", "output": "1"},
            {"input": "pwwkew", "output": "3"}
        ]),
        "hidden_test_cases": json.dumps([
            {"input": "", "output": "0"},
            {"input": " ", "output": "1"},
            {"input": "au", "output": "2"},
            {"input": "dvdf", "output": "3"},
            {"input": "anviaj", "output": "5"}
        ])
    }
]


async def seed_initial_coding_problems(db: AsyncSession) -> None:
    """Inserts initial canonical coding interview problems if they don't already exist."""
    try:
        count_res = await db.execute(select(func.count(CodingProblem.id)))
        count = count_res.scalar() or 0
        if count >= len(INITIAL_PROBLEMS):
            return

        for p_data in INITIAL_PROBLEMS:
            existing_res = await db.execute(select(CodingProblem).where(CodingProblem.slug == p_data["slug"]))
            existing = existing_res.scalar_one_or_none()
            if not existing:
                problem = CodingProblem(**p_data)
                db.add(problem)

        await db.commit()
        logger.info("Successfully seeded canonical coding interview problems.")
    except Exception as exc:
        await db.rollback()
        logger.warning(f"Error while checking/seeding coding problems: {exc}")
