import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.model import Interview
from app.modules.practice.model import PracticeProgress, PracticeQuestion
from app.modules.practice.schema import (
    BookmarkResponse,
    DifficultyProgressItem,
    MasteryStats,
    PracticeAchievement,
    PracticeHistoryItem,
    PracticeHistoryResponse,
    PracticeMission,
    PracticeNotification,
    PracticeProgressResponse,
    PracticeQuestionDetailResponse,
    PracticeQuestionListResponse,
    PracticeQuestionSummary,
    PracticeStatsResponse,
    SolveQuestionResponse,
    StreakStats,
    TechnologyListResponse,
    TechnologySummary,
    TopicListResponse,
    TopicMasteryItem,
    TopicProgressItem,
    TopicSummary,
    XpStats,
)

# ============================================================
# CANONICAL BASELINE QUESTIONS (SUPPLEMENTS EXISTING INTERVIEW QUESTIONS)
# ============================================================
CANONICAL_QUESTIONS = [
    {
        "question": "Explain the difference between optimistic and pessimistic locking in database transaction management.",
        "topic": "Database Architecture",
        "difficulty": "Medium",
        "role": "Backend Engineer",
        "question_type": "Technical",
        "explanation": "Pessimistic locking assumes conflicting concurrent updates will happen, acquiring a lock on records upfront (e.g. SELECT FOR UPDATE), which prevents other transactions from modifying the record until committed. Optimistic locking assumes conflicts are rare, checking a version or timestamp column upon write; if the version changed, the transaction aborts and retries. Optimistic locking is ideal for high-read throughput with low write contention.",
    },
    {
        "question": "How would you design a scalable rate limiting algorithm for a public API gateway?",
        "topic": "System Design",
        "difficulty": "Hard",
        "role": "System Architect",
        "question_type": "System Design",
        "explanation": "A distributed rate limiter typically employs either the Token Bucket or Sliding Window Counter algorithm. Using Redis with atomic Lua scripts guarantees low latency and prevents race conditions. Keys are structured around client ID/IP with TTL expiry matching the rate window.",
    },
    {
        "question": "What are the core trade-offs between monolithic and microservice architectures?",
        "topic": "System Architecture",
        "difficulty": "Medium",
        "role": "Software Engineer",
        "question_type": "System Design",
        "explanation": "Monoliths offer simpler deployments, easier debugging, transaction management, and zero inter-service network latency. Microservices offer decoupled team autonomy, targeted vertical/horizontal scaling, and technology diversity, but introduce network latency, distributed transaction complexity, and operational overhead.",
    },
    {
        "question": "Describe how event loops work in asynchronous JavaScript and Python asyncio.",
        "topic": "Concurrency",
        "difficulty": "Medium",
        "role": "Software Engineer",
        "question_type": "Technical",
        "explanation": "Event loops coordinate single-threaded concurrency by maintaining queues of tasks, microtasks, and timers. When an asynchronous I/O operation is initiated (network/disk), control returns to the loop to execute other ready tasks until the OS signals I/O completion.",
    },
    {
        "question": "How do B-Tree and LSM-Tree storage engines differ in their read and write characteristics?",
        "topic": "Database Internals",
        "difficulty": "Hard",
        "role": "Backend Engineer",
        "question_type": "Technical",
        "explanation": "B-Trees organize data into fixed-size pages and update them in place, providing predictable O(log N) reads with random write amplification. LSM-Trees (Log-Structured Merge-Trees) buffer writes sequentially in memory (MemTable) before flushing to immutable disk files (SSTables), providing superior write throughput at the cost of compaction overhead and read amplification.",
    },
]


def _generate_question_id(question_text: str) -> str:
    cleaned = question_text.strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def _normalize_difficulty(val: str | None) -> str:
    if not val:
        return "Medium"
    cleaned = val.strip().lower()
    if cleaned in {"easy", "beginner"}:
        return "Easy"
    if cleaned in {"hard", "difficult", "advanced"}:
        return "Hard"
    return "Medium"


def _normalize_topic(val: str | None) -> str:
    if not val or not val.strip():
        return "General"
    return val.strip().title()


def _infer_question_type(question: str, topic: str) -> str:
    q_lower = question.lower()
    t_lower = topic.lower()
    if any(k in q_lower or k in t_lower for k in ["design", "architecture", "scale", "system", "gateway"]):
        return "System Design"
    if any(k in q_lower for k in ["tell me about a time", "situation", "conflict", "leadership", "team"]):
        return "Behavioral"
    if any(k in q_lower for k in ["what is", "difference between", "explain concept", "trade-off"]):
        return "Conceptual"
    return "Technical"


def slugify(text: str) -> str:
    cleaned = text.lower().replace("+", "-plus").replace(".", "-").replace("/", "-")
    chars = [c if c.isalnum() or c == "-" else "-" for c in cleaned]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


_PLATFORM_CATALOG_CACHE: dict[str, dict] | None = None


async def load_all_platform_questions(db: AsyncSession) -> dict[str, dict]:
    """
    Dynamically loads and unifies all questions from the PostgreSQL practice_questions table,
    with in-memory caching and fallback to canonical_bank.json and interviews table.
    """
    global _PLATFORM_CATALOG_CACHE
    if _PLATFORM_CATALOG_CACHE is not None and len(_PLATFORM_CATALOG_CACHE) >= 5000:
        return _PLATFORM_CATALOG_CACHE

    stmt = select(PracticeQuestion)
    result = await db.execute(stmt)
    db_questions = result.scalars().all()

    catalog: dict[str, dict] = {}
    if db_questions:
        for q in db_questions:
            catalog[q.id] = {
                "id": q.id,
                "question": q.question,
                "technology": q.technology,
                "technology_slug": q.technology_slug,
                "topic": q.topic,
                "topic_slug": q.topic_slug,
                "subtopic": q.subtopic,
                "difficulty": q.difficulty,
                "role": q.role or "Software Engineer",
                "question_type": q.question_type or "Technical",
                "explanation": q.explanation or "",
                "source": q.source,
            }
        _PLATFORM_CATALOG_CACHE = catalog
        return catalog

    # Fallback to canonical_bank.json if available
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canonical_bank.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    catalog[item["id"]] = item
            _PLATFORM_CATALOG_CACHE = catalog
            return catalog
        except Exception:
            pass

    # Secondary fallback to CANONICAL_QUESTIONS and interviews table
    for cq in CANONICAL_QUESTIONS:
        qid = _generate_question_id(cq["question"])
        catalog[qid] = {
            "id": qid,
            "question": cq["question"],
            "technology": "General",
            "technology_slug": "general",
            "topic": cq["topic"],
            "topic_slug": slugify(cq["topic"]),
            "subtopic": "General",
            "difficulty": cq["difficulty"],
            "role": cq["role"],
            "question_type": cq["question_type"],
            "explanation": cq["explanation"],
            "source": "canonical",
        }

    stmt_int = select(
        Interview.questions,
        Interview.question_evaluations,
        Interview.job_role,
        Interview.difficulty,
    )
    result_int = await db.execute(stmt_int)
    for row in result_int.all():
        q_raw, eval_raw, job_role, int_diff = row
        if not q_raw:
            continue
        try:
            qs = json.loads(q_raw)
            if isinstance(qs, list):
                for q_item in qs:
                    q_text = str(q_item.get("question", "")).strip() if isinstance(q_item, dict) else str(q_item).strip()
                    if len(q_text) < 10:
                        continue
                    qid = _generate_question_id(q_text)
                    if qid not in catalog:
                        top = _normalize_topic(q_item.get("topic") if isinstance(q_item, dict) else job_role)
                        diff = _normalize_difficulty(q_item.get("difficulty") if isinstance(q_item, dict) else int_diff)
                        catalog[qid] = {
                            "id": qid,
                            "question": q_text,
                            "technology": "General",
                            "technology_slug": "general",
                            "topic": top,
                            "topic_slug": slugify(top),
                            "subtopic": "General",
                            "difficulty": diff,
                            "role": job_role or "Technical Interview",
                            "question_type": _infer_question_type(q_text, top),
                            "explanation": "",
                            "source": "interview",
                        }
        except Exception:
            continue

    _PLATFORM_CATALOG_CACHE = catalog
    return catalog


async def get_technologies_summary(
    db: AsyncSession,
    user_id: UUID,
    search: str | None = None,
) -> TechnologyListResponse:
    """
    Returns summary statistics for each technology in the question bank.
    Includes total questions, solved, remaining, mastery percentage, XP earned, and topic count.
    """
    catalog = await load_all_platform_questions(db)
    all_questions = list(catalog.values())

    stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    prog_res = await db.execute(stmt)
    user_progress = {p.question_id: p for p in prog_res.scalars().all()}

    # Group by technology
    tech_map: dict[str, list[dict]] = defaultdict(list)
    for q in all_questions:
        tech_name = q.get("technology") or "General"
        tech_map[tech_name].append(q)

    tech_summaries: list[TechnologySummary] = []
    total_solved_all = 0

    for tech_name, t_questions in tech_map.items():
        total_q = len(t_questions)
        solved_q = [
            q for q in t_questions
            if user_progress.get(q["id"]) and user_progress[q["id"]].solved
        ]
        solved_count = len(solved_q)
        total_solved_all += solved_count
        remaining_count = max(0, total_q - solved_count)
        mastery = round((solved_count / total_q) * 100.0, 1) if total_q > 0 else 0.0

        # XP earned in this technology
        xp_earned = 0
        for sq in solved_q:
            diff = sq.get("difficulty", "Medium").lower()
            base_xp = 10 if diff == "easy" else (35 if diff == "hard" else 20)
            xp_earned += (base_xp + 15)

        topics_count = len({q.get("topic", "General") for q in t_questions})
        slug = t_questions[0].get("technology_slug") or slugify(tech_name)

        tech_summaries.append(
            TechnologySummary(
                technology=tech_name,
                slug=slug,
                total_questions=total_q,
                solved=solved_count,
                remaining=remaining_count,
                mastery_percentage=mastery,
                xp_earned=xp_earned,
                topics_count=topics_count,
            )
        )

    # Filter by search if provided
    if search and search.strip():
        term = search.strip().lower()
        tech_summaries = [
            t for t in tech_summaries
            if term in t.technology.lower() or term in t.slug.lower()
        ]

    # Sort technologies: technologies with active solved first, then alphabetically
    tech_summaries.sort(key=lambda x: (-x.solved, x.technology))

    return TechnologyListResponse(
        technologies=tech_summaries,
        total_technologies=len(tech_summaries),
        total_questions=len(all_questions),
        total_solved=total_solved_all,
    )


async def get_topics_summary(
    db: AsyncSession,
    user_id: UUID,
    technology_slug: str,
) -> TopicListResponse:
    """
    Returns summary statistics for all topics within a specific technology.
    """
    catalog = await load_all_platform_questions(db)
    all_questions = list(catalog.values())

    stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    prog_res = await db.execute(stmt)
    user_progress = {p.question_id: p for p in prog_res.scalars().all()}

    t_clean = technology_slug.strip().lower()
    matching_questions = [
        q for q in all_questions
        if q.get("technology_slug", "").lower() == t_clean or q.get("technology", "").lower() == t_clean
    ]

    if not matching_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Technology '{technology_slug}' not found in question bank.",
        )

    tech_name = matching_questions[0].get("technology", technology_slug)
    tech_slug = matching_questions[0].get("technology_slug", technology_slug)

    # Group by topic
    topic_map: dict[str, list[dict]] = defaultdict(list)
    for q in matching_questions:
        top_name = q.get("topic", "General")
        topic_map[top_name].append(q)

    topic_summaries: list[TopicSummary] = []
    total_solved_tech = 0

    for top_name, top_questions in topic_map.items():
        total_q = len(top_questions)
        solved_q = [
            q for q in top_questions
            if user_progress.get(q["id"]) and user_progress[q["id"]].solved
        ]
        solved_count = len(solved_q)
        total_solved_tech += solved_count
        remaining_count = max(0, total_q - solved_count)
        mastery = round((solved_count / total_q) * 100.0, 1) if total_q > 0 else 0.0
        slug = top_questions[0].get("topic_slug") or slugify(top_name)

        topic_summaries.append(
            TopicSummary(
                technology=tech_name,
                technology_slug=tech_slug,
                topic=top_name,
                slug=slug,
                total_questions=total_q,
                solved=solved_count,
                remaining=remaining_count,
                mastery_percentage=mastery,
            )
        )

    # Sort topics: solved first, then alphabetically
    topic_summaries.sort(key=lambda x: (-x.solved, x.topic))

    return TopicListResponse(
        technology=tech_name,
        technology_slug=tech_slug,
        topics=topic_summaries,
        total_topics=len(topic_summaries),
        total_questions=len(matching_questions),
        total_solved=total_solved_tech,
    )


async def get_practice_questions_list(
    db: AsyncSession,
    user_id: UUID,
    technology: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PracticeQuestionListResponse:
    # 1. Load question catalog
    catalog = await load_all_platform_questions(db)
    all_questions = list(catalog.values())

    # 2. Load user's practice progress
    stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    prog_res = await db.execute(stmt)
    user_progress = {p.question_id: p for p in prog_res.scalars().all()}

    # 3. Available filter facets
    if technology and technology.strip() and technology.strip().lower() != "all":
        t_clean = technology.strip().lower()
        tech_matched = [
            q for q in all_questions
            if q.get("technology_slug", "").lower() == t_clean or q.get("technology", "").lower() == t_clean
        ]
        all_topics = sorted(list({q["topic"] for q in tech_matched})) if tech_matched else []
    else:
        all_topics = sorted(list({q["topic"] for q in all_questions}))

    all_difficulties = ["Easy", "Medium", "Hard"]
    all_types = sorted(list({q.get("question_type", "Technical") for q in all_questions}))

    # 4. Filter list
    filtered: list[PracticeQuestionSummary] = []
    search_clean = (search or "").strip().lower()

    for q in all_questions:
        qid = q["id"]
        prog = user_progress.get(qid)
        is_solved = bool(prog.solved) if prog else False
        is_bookmarked = bool(prog.bookmarked) if prog else False
        attempts = int(prog.attempts) if prog else 0

        # Technology filter
        if technology and technology.strip() and technology.strip().lower() != "all":
            t_clean = technology.strip().lower()
            q_tech = q.get("technology", "").lower()
            q_tech_slug = q.get("technology_slug", "").lower()
            if (
                t_clean != q_tech
                and t_clean != q_tech_slug
                and t_clean not in q_tech_slug.split("-")
                and t_clean not in q_tech
            ):
                continue

        # Topic filter
        if topic and topic.strip() and topic.strip().lower() != "all":
            top_clean = topic.strip().lower()
            q_topic = q.get("topic", "").lower()
            q_topic_slug = q.get("topic_slug", "").lower()
            if (
                top_clean != q_topic
                and top_clean != q_topic_slug
                and top_clean not in q_topic_slug.split("-")
                and top_clean not in q_topic
            ):
                continue

        # Difficulty filter
        if difficulty and difficulty.strip() and difficulty.strip().lower() != "all":
            if q["difficulty"].lower() != difficulty.strip().lower():
                continue

        # Question type filter
        if question_type and question_type.strip() and question_type.strip().lower() != "all":
            if q.get("question_type", "").lower() != question_type.strip().lower():
                continue

        # Status filter (all, solved, unsolved, bookmarked)
        if status_filter:
            s_clean = status_filter.strip().lower()
            if s_clean == "solved" and not is_solved:
                continue
            if s_clean == "unsolved" and is_solved:
                continue
            if s_clean == "bookmarked" and not is_bookmarked:
                continue

        # Search filter
        if search_clean:
            matches_text = search_clean in q["question"].lower()
            matches_topic = search_clean in q.get("topic", "").lower()
            matches_tech = search_clean in q.get("technology", "").lower()
            matches_role = q.get("role") and search_clean in q["role"].lower()
            if not (matches_text or matches_topic or matches_tech or matches_role):
                continue

        diff_lower = q["difficulty"].lower()
        base_xp = 10 if diff_lower == "easy" else (35 if diff_lower == "hard" else 20)
        xp_reward = base_xp + (0 if is_solved else 15)

        filtered.append(
            PracticeQuestionSummary(
                id=qid,
                question=q["question"],
                technology=q.get("technology", "General"),
                technology_slug=q.get("technology_slug", "general"),
                topic=q.get("topic", "General"),
                topic_slug=q.get("topic_slug", "general"),
                subtopic=q.get("subtopic", "General"),
                difficulty=q["difficulty"],
                role=q.get("role"),
                question_type=q.get("question_type", "Technical"),
                explanation=q.get("explanation"),
                solved=is_solved,
                bookmarked=is_bookmarked,
                attempts=attempts,
                xp_reward=xp_reward,
            )
        )

    # 5. Pagination
    total = len(filtered)
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_items = filtered[start_idx:end_idx]

    return PracticeQuestionListResponse(
        questions=paged_items,
        total=total,
        page=page,
        page_size=page_size,
        topics=all_topics,
        difficulties=all_difficulties,
        question_types=all_types,
    )


async def get_practice_question_detail(
    db: AsyncSession,
    user_id: UUID,
    question_id: str,
) -> PracticeQuestionDetailResponse:
    catalog = await load_all_platform_questions(db)
    if question_id not in catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice question '{question_id}' not found.",
        )

    q = catalog[question_id]

    # Calculate previous and next question IDs
    keys = list(catalog.keys())
    curr_idx = keys.index(question_id)
    prev_id = keys[curr_idx - 1] if curr_idx > 0 else None
    next_id = keys[curr_idx + 1] if curr_idx < len(keys) - 1 else None

    # Load user progress
    stmt = (
        select(PracticeProgress)
        .where(
            PracticeProgress.user_id == user_id,
            PracticeProgress.question_id == question_id,
        )
    )
    res = await db.execute(stmt)
    prog = res.scalar_one_or_none()

    is_solved = bool(prog.solved) if prog else False
    is_bookmarked = bool(prog.bookmarked) if prog else False
    attempts = int(prog.attempts) if prog else 0
    last_ans = prog.last_answer if prog else None
    last_att = prog.last_attempted_at.isoformat() if prog and prog.last_attempted_at else None

    diff_lower = q["difficulty"].lower()
    base_xp = 10 if diff_lower == "easy" else (35 if diff_lower == "hard" else 20)
    xp_reward = base_xp + (0 if is_solved else 15)

    return PracticeQuestionDetailResponse(
        id=q["id"],
        question=q["question"],
        technology=q.get("technology", "General"),
        technology_slug=q.get("technology_slug", "general"),
        topic=q["topic"],
        topic_slug=q.get("topic_slug", "general"),
        subtopic=q.get("subtopic", "General"),
        difficulty=q["difficulty"],
        role=q.get("role"),
        question_type=q.get("question_type", "Technical"),
        explanation=q.get("explanation") or "",
        solved=is_solved,
        bookmarked=is_bookmarked,
        attempts=attempts,
        xp_reward=xp_reward,
        last_answer=last_ans,
        last_attempted_at=last_att,
        previous_id=prev_id,
        next_id=next_id,
    )


async def solve_practice_question(
    db: AsyncSession,
    user_id: UUID,
    question_id: str,
    answer: str | None = None,
    solved: bool = True,
) -> SolveQuestionResponse:
    catalog = await load_all_platform_questions(db)
    if question_id not in catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    q = catalog[question_id]

    # Pre-solve state for XP & level difference
    stmt_all = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    res_all = await db.execute(stmt_all)
    all_records = list(res_all.scalars().all())
    _, old_xp_stats = _calculate_xp_from_records(catalog, all_records)

    stmt = select(PracticeProgress).where(
        PracticeProgress.user_id == user_id,
        PracticeProgress.question_id == question_id,
    )
    res = await db.execute(stmt)
    prog = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    was_previously_solved = bool(prog.solved) if prog else False

    if prog is None:
        prog = PracticeProgress(
            user_id=user_id,
            question_id=question_id,
            solved=solved,
            bookmarked=False,
            attempts=1,
            last_answer=answer.strip() if answer else None,
            last_attempted_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(prog)
    else:
        prog.solved = solved
        prog.attempts += 1
        if answer is not None:
            prog.last_answer = answer.strip()
        prog.last_attempted_at = now
        prog.updated_at = now

    await db.commit()
    await db.refresh(prog)

    # Post-solve records
    res_all_after = await db.execute(stmt_all)
    after_records = list(res_all_after.scalars().all())
    new_xp, new_xp_stats = _calculate_xp_from_records(catalog, after_records)
    streak_stats = _calculate_streak_from_records(after_records)
    missions = _evaluate_missions_from_records(catalog, after_records)

    # Calculate XP earned this action
    xp_earned = 0
    bonus_xp = 0
    if solved and not was_previously_solved:
        diff = q["difficulty"].lower()
        base_xp = 10 if diff == "easy" else (35 if diff == "hard" else 20)
        xp_earned += base_xp
        if prog.attempts == 1:
            bonus_xp += 15
        if prog.last_answer and len(prog.last_answer.strip()) >= 50:
            bonus_xp += 10
        xp_earned += bonus_xp

    leveled_up = new_xp_stats.level > old_xp_stats.level
    completed_mission_ids = [m.id for m in missions if m.completed]

    # Evaluate achievements in PostgreSQL
    from app.modules.achievements.service import evaluate_user_achievements
    _, newly_unlocked = await evaluate_user_achievements(db, user_id, catalog)

    # Persist real notifications for practice events
    try:
        from app.modules.notifications.service import NotificationService
        from app.modules.notifications.schema import NotificationType

        if leveled_up:
            await NotificationService.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.LEVEL_UP.value,
                title=f"Level Up! Level {new_xp_stats.level}",
                message=f"You reached Level {new_xp_stats.level} rank: {new_xp_stats.level_title} with {new_xp} XP!",
                icon="⭐",
                event_key=f"level_up:{user_id}:{new_xp_stats.level}",
                metadata={"level": new_xp_stats.level, "level_title": new_xp_stats.level_title, "total_xp": new_xp},
                action_url="/practice",
                priority="high",
            )

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for m in missions:
            if m.completed:
                event_key = f"mission_completed:{user_id}:{today_str}:{m.id}"
                await NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    type=NotificationType.MISSION_COMPLETED.value,
                    title=f"Daily Quest Complete: {m.title}",
                    message=f"You completed '{m.description}' and earned +{m.xp_reward} XP bonus!",
                    icon=m.icon or "🎯",
                    event_key=event_key,
                    metadata={"mission_id": m.id, "xp_reward": m.xp_reward, "date": today_str},
                    action_url="/practice",
                    priority="normal",
                )

        if xp_earned > 0:
            q_title = q["question"][:50] + ("..." if len(q["question"]) > 50 else "")
            event_key = f"xp_earned:{user_id}:{prog.question_id}:{int(now.timestamp())}"
            await NotificationService.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.XP_EARNED.value,
                title="XP Earned",
                message=f"You earned +{xp_earned} XP for solving '{q_title}' in {q['topic']}.",
                icon="✓",
                event_key=event_key,
                metadata={"question_id": prog.question_id, "xp_earned": xp_earned, "topic": q["topic"]},
                action_url="/practice",
                priority="normal",
            )

        solved_count = sum(1 for r in after_records if r.solved)
        for m_count in [5, 25, 50, 100, 250, 500]:
            if solved_count == m_count:
                await NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    type=NotificationType.PRACTICE_MILESTONE.value,
                    title=f"Milestone Reached: {m_count} Questions Solved!",
                    message=f"Congratulations! You have solved {m_count} technical practice problems.",
                    icon="🎯",
                    event_key=f"practice_milestone:{user_id}:{m_count}",
                    metadata={"milestone": m_count, "solved_count": solved_count},
                    action_url="/practice",
                    priority="normal",
                )
    except Exception as notif_err:
        pass

    msg = "Question marked as solved!" if solved else "Question marked as unsolved."
    if newly_unlocked:
        msg += f" 🏆 Achievement Unlocked: {newly_unlocked[0].name} (+{newly_unlocked[0].xp_reward} XP)!"

    return SolveQuestionResponse(
        success=True,
        solved=prog.solved,
        attempts=prog.attempts,
        message=msg,
        xp_earned=xp_earned,
        bonus_xp=bonus_xp,
        total_xp=new_xp,
        current_level=new_xp_stats.level,
        level_title=new_xp_stats.level_title,
        leveled_up=leveled_up,
        streak_days=streak_stats.current_streak,
        completed_missions=completed_mission_ids,
    )


async def bookmark_practice_question(
    db: AsyncSession,
    user_id: UUID,
    question_id: str,
    bookmarked: bool = True,
) -> BookmarkResponse:
    catalog = await load_all_platform_questions(db)
    if question_id not in catalog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    stmt = select(PracticeProgress).where(
        PracticeProgress.user_id == user_id,
        PracticeProgress.question_id == question_id,
    )
    res = await db.execute(stmt)
    prog = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if prog is None:
        prog = PracticeProgress(
            user_id=user_id,
            question_id=question_id,
            solved=False,
            bookmarked=bookmarked,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        db.add(prog)
    else:
        prog.bookmarked = bookmarked
        prog.updated_at = now

    await db.commit()

    msg = "Question bookmarked successfully" if bookmarked else "Bookmark removed"
    return BookmarkResponse(
        success=True,
        bookmarked=bookmarked,
        message=msg,
    )


async def get_user_practice_progress(
    db: AsyncSession,
    user_id: UUID,
) -> PracticeProgressResponse:
    catalog = await load_all_platform_questions(db)
    total_q = len(catalog)

    stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    res = await db.execute(stmt)
    records = res.scalars().all()

    solved_set = {p.question_id for p in records if p.solved}
    bookmarked_set = {p.question_id for p in records if p.bookmarked}

    solved_count = len(solved_set.intersection(catalog.keys()))
    bookmarked_count = len(bookmarked_set.intersection(catalog.keys()))
    unsolved_count = max(0, total_q - solved_count)
    completion_pct = round((solved_count / total_q) * 100, 1) if total_q > 0 else 0.0

    # Topic breakdown
    topic_totals: dict[str, int] = defaultdict(int)
    topic_solved: dict[str, int] = defaultdict(int)
    for qid, q in catalog.items():
        t = q["topic"]
        topic_totals[t] += 1
        if qid in solved_set:
            topic_solved[t] += 1

    topic_progress: list[TopicProgressItem] = []
    for t in sorted(topic_totals.keys()):
        tot = topic_totals[t]
        sol = topic_solved[t]
        pct = round((sol / tot) * 100, 1) if tot > 0 else 0.0
        topic_progress.append(TopicProgressItem(topic=t, total=tot, solved=sol, percentage=pct))

    # Difficulty breakdown
    diff_totals: dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}
    diff_solved: dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}
    for qid, q in catalog.items():
        d = q["difficulty"]
        if d in diff_totals:
            diff_totals[d] += 1
            if qid in solved_set:
                diff_solved[d] += 1

    difficulty_progress: list[DifficultyProgressItem] = []
    for d in ["Easy", "Medium", "Hard"]:
        tot = diff_totals[d]
        sol = diff_solved[d]
        pct = round((sol / tot) * 100, 1) if tot > 0 else 0.0
        difficulty_progress.append(
            DifficultyProgressItem(difficulty=d, total=tot, solved=sol, percentage=pct)
        )

    return PracticeProgressResponse(
        total_questions=total_q,
        solved_count=solved_count,
        unsolved_count=unsolved_count,
        bookmarked_count=bookmarked_count,
        completion_percentage=completion_pct,
        topic_progress=topic_progress,
        difficulty_progress=difficulty_progress,
    )


async def get_user_practice_history(
    db: AsyncSession,
    user_id: UUID,
) -> PracticeHistoryResponse:
    catalog = await load_all_platform_questions(db)

    stmt = (
        select(PracticeProgress)
        .where(
            PracticeProgress.user_id == user_id,
            PracticeProgress.attempts > 0,
        )
        .order_by(PracticeProgress.last_attempted_at.desc().nullslast())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    history: list[PracticeHistoryItem] = []
    for p in records:
        q = catalog.get(p.question_id)
        if not q:
            continue
        history.append(
            PracticeHistoryItem(
                question_id=p.question_id,
                question=q["question"],
                topic=q["topic"],
                difficulty=q["difficulty"],
                solved=bool(p.solved),
                attempts=p.attempts,
                last_answer=p.last_answer,
                last_attempted_at=p.last_attempted_at.isoformat() if p.last_attempted_at else None,
            )
        )

    return PracticeHistoryResponse(history=history, total=len(history))


# ============================================================
# STATS ENGINE: XP, MASTERY, STREAK, MISSIONS, ACHIEVEMENTS, NOTIFICATIONS
# ============================================================

def _calculate_xp_from_records(
    catalog: dict[str, dict], records: list[PracticeProgress]
) -> tuple[int, XpStats]:
    total_xp = 0
    for p in records:
        if not p.solved:
            continue
        q = catalog.get(p.question_id)
        diff = q["difficulty"].lower() if q else "medium"
        base_xp = 10 if diff == "easy" else (35 if diff == "hard" else 20)
        total_xp += base_xp

        # First-attempt solve bonus
        if p.attempts == 1:
            total_xp += 15

        # Detailed solution bonus
        if p.last_answer and len(p.last_answer.strip()) >= 50:
            total_xp += 10

    # Level thresholds
    if total_xp < 100:
        lvl = 1
        title = "Novice Problem Solver"
        cur_xp = total_xp
        nxt_xp = 100
        pct = round((cur_xp / nxt_xp) * 100, 1)
    elif total_xp < 250:
        lvl = 2
        title = "Code Practitioner"
        cur_xp = total_xp - 100
        nxt_xp = 150
        pct = round((cur_xp / nxt_xp) * 100, 1)
    elif total_xp < 500:
        lvl = 3
        title = "Technical Specialist"
        cur_xp = total_xp - 250
        nxt_xp = 250
        pct = round((cur_xp / nxt_xp) * 100, 1)
    elif total_xp < 900:
        lvl = 4
        title = "Lead Problem Solver"
        cur_xp = total_xp - 500
        nxt_xp = 400
        pct = round((cur_xp / nxt_xp) * 100, 1)
    else:
        lvl = 5
        title = "Staff Architect"
        cur_xp = min(total_xp - 900, 600)
        nxt_xp = 600
        pct = round(min(100.0, (cur_xp / nxt_xp) * 100), 1)

    xp_stats = XpStats(
        total_xp=total_xp,
        level=lvl,
        level_title=title,
        current_level_xp=cur_xp,
        next_level_xp=nxt_xp,
        progress_pct=pct,
    )
    return total_xp, xp_stats


def _calculate_streak_from_records(records: list[PracticeProgress]) -> StreakStats:
    now = datetime.now(timezone.utc)
    today = now.date()

    dates: set = set()
    for p in records:
        if p.last_attempted_at:
            dates.add(p.last_attempted_at.astimezone(timezone.utc).date())

    is_active_today = today in dates
    sorted_dates = sorted(list(dates), reverse=True)
    last_date_str = sorted_dates[0].isoformat() if sorted_dates else None

    # Calculate current streak
    current_streak = 0
    if is_active_today:
        check_date = today
        while check_date in dates:
            current_streak += 1
            check_date -= timedelta(days=1)
    else:
        # Check yesterday
        yesterday = today - timedelta(days=1)
        if yesterday in dates:
            check_date = yesterday
            while check_date in dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        else:
            current_streak = 0

    # Calculate longest streak
    longest_streak = current_streak
    if dates:
        ascending_dates = sorted(list(dates))
        temp_streak = 1
        for i in range(1, len(ascending_dates)):
            if (ascending_dates[i] - ascending_dates[i - 1]).days == 1:
                temp_streak += 1
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
            elif (ascending_dates[i] - ascending_dates[i - 1]).days > 1:
                temp_streak = 1

    return StreakStats(
        current_streak=current_streak,
        longest_streak=longest_streak,
        is_active_today=is_active_today,
        last_practiced_date=last_date_str,
    )


def _evaluate_missions_from_records(
    catalog: dict[str, dict], records: list[PracticeProgress]
) -> list[PracticeMission]:
    now = datetime.now(timezone.utc)
    today = now.date()

    today_solved = 0
    today_med_hard = 0
    today_topics: set[str] = set()
    today_detailed = 0

    for p in records:
        if not p.last_attempted_at:
            continue
        if p.last_attempted_at.astimezone(timezone.utc).date() != today:
            continue

        q = catalog.get(p.question_id)
        if q:
            today_topics.add(q["topic"])
            if p.solved:
                today_solved += 1
                if q["difficulty"].lower() in ["medium", "hard"]:
                    today_med_hard += 1

        if p.last_answer and len(p.last_answer.strip()) >= 50:
            today_detailed += 1

    return [
        PracticeMission(
            id="daily_warmup",
            title="Daily Warmup",
            description="Solve at least 1 question today",
            icon="⚡",
            progress=min(today_solved, 1),
            target=1,
            completed=today_solved >= 1,
            xp_reward=25,
        ),
        PracticeMission(
            id="depth_challenge",
            title="Depth Challenge",
            description="Solve a Medium or Hard question",
            icon="🧠",
            progress=min(today_med_hard, 1),
            target=1,
            completed=today_med_hard >= 1,
            xp_reward=35,
        ),
        PracticeMission(
            id="topic_explorer",
            title="Topic Explorer",
            description="Practice across 2 different topics",
            icon="🌐",
            progress=min(len(today_topics), 2),
            target=2,
            completed=len(today_topics) >= 2,
            xp_reward=30,
        ),
        PracticeMission(
            id="thorough_solution",
            title="Detailed Solution",
            description="Save comprehensive solution notes (>50 chars)",
            icon="✍️",
            progress=min(today_detailed, 1),
            target=1,
            completed=today_detailed >= 1,
            xp_reward=20,
        ),
    ]


def _evaluate_mastery_from_records(
    catalog: dict[str, dict], records: list[PracticeProgress]
) -> MasteryStats:
    topic_totals: dict[str, int] = defaultdict(int)
    topic_solved: dict[str, int] = defaultdict(int)

    solved_qids = {p.question_id for p in records if p.solved}

    for qid, q in catalog.items():
        t = q["topic"]
        topic_totals[t] += 1
        if qid in solved_qids:
            topic_solved[t] += 1

    items: list[TopicMasteryItem] = []
    mastered = 0
    proficient = 0

    for t, tot in sorted(topic_totals.items()):
        sol = topic_solved[t]
        pct = round((sol / tot) * 100, 1) if tot > 0 else 0.0
        if pct >= 80:
            status_str = "Mastered"
            mastered += 1
        elif pct >= 50:
            status_str = "Proficient"
            proficient += 1
        elif sol > 0:
            status_str = "Practicing"
        else:
            status_str = "Unexplored"

        items.append(
            TopicMasteryItem(
                topic=t,
                total=tot,
                solved=sol,
                percentage=pct,
                status=status_str,
            )
        )

    items.sort(key=lambda x: (x.solved, x.percentage), reverse=True)
    total_q = len(catalog)
    total_sol = len(solved_qids)
    overall_pct = round((total_sol / total_q) * 100, 1) if total_q > 0 else 0.0

    return MasteryStats(
        overall_percentage=overall_pct,
        mastered_topics=mastered,
        proficient_topics=proficient,
        total_topics=len(topic_totals),
        top_topics=items[:8],
    )


def _evaluate_achievements(
    catalog: dict[str, dict],
    records: list[PracticeProgress],
    total_xp: int,
    streak: StreakStats,
    missions: list[PracticeMission],
) -> list[PracticeAchievement]:
    solved_count = sum(1 for p in records if p.solved)
    distinct_topics = {
        catalog[p.question_id]["topic"]
        for p in records
        if p.question_id in catalog and p.solved
    }
    completed_missions_count = sum(1 for m in missions if m.completed)

    return [
        PracticeAchievement(
            id="first_solve",
            title="First Step",
            description="Solve your first practice question",
            icon="🎯",
            unlocked=solved_count >= 1,
            progress=f"{min(solved_count, 1)} / 1",
            category="solve",
        ),
        PracticeAchievement(
            id="streak_3",
            title="Consistent Practitioner",
            description="Maintain a 3-day practice streak",
            icon="🔥",
            unlocked=streak.current_streak >= 3 or streak.longest_streak >= 3,
            progress=f"{min(max(streak.current_streak, streak.longest_streak), 3)} / 3 days",
            category="streak",
        ),
        PracticeAchievement(
            id="xp_100",
            title="Century Club",
            description="Earn 100+ Practice XP points",
            icon="⭐",
            unlocked=total_xp >= 100,
            progress=f"{min(total_xp, 100)} / 100 XP",
            category="xp",
        ),
        PracticeAchievement(
            id="multi_topic",
            title="Multi-Disciplinary",
            description="Practice across 3+ unique topics",
            icon="🧭",
            unlocked=len(distinct_topics) >= 3,
            progress=f"{min(len(distinct_topics), 3)} / 3 topics",
            category="mastery",
        ),
        PracticeAchievement(
            id="daily_all",
            title="Daily Achiever",
            description="Complete all daily practice missions",
            icon="🏆",
            unlocked=completed_missions_count == len(missions),
            progress=f"{completed_missions_count} / {len(missions)} missions",
            category="mission",
        ),
    ]


def _generate_notifications(
    catalog: dict[str, dict],
    records: list[PracticeProgress],
    xp_stats: XpStats,
    streak: StreakStats,
    missions: list[PracticeMission],
    achievements: list[PracticeAchievement],
) -> list[PracticeNotification]:
    notifications: list[PracticeNotification] = []

    solved_records = [p for p in records if p.solved and p.last_attempted_at]
    solved_records.sort(key=lambda p: p.last_attempted_at, reverse=True)

    # 1. Level Notification
    if xp_stats.level > 1:
        notifications.append(
            PracticeNotification(
                id=f"lvl_{xp_stats.level}",
                type="level_up",
                title=f"Level {xp_stats.level} Achieved!",
                message=f"You earned the rank of {xp_stats.level_title} with {xp_stats.total_xp} XP.",
                timestamp=solved_records[0].last_attempted_at.isoformat() if solved_records else datetime.now(timezone.utc).isoformat(),
                icon="🎉",
            )
        )

    # 2. Streak Notification
    if streak.current_streak >= 1:
        notifications.append(
            PracticeNotification(
                id=f"streak_{streak.current_streak}",
                type="streak",
                title=f"{streak.current_streak}-Day Streak Active! 🔥",
                message=f"You have practiced consecutively for {streak.current_streak} day{'s' if streak.current_streak > 1 else ''}. Keep it up!",
                timestamp=datetime.now(timezone.utc).isoformat(),
                icon="🔥",
            )
        )

    # 3. Completed Mission Notifications
    for m in missions:
        if m.completed:
            notifications.append(
                PracticeNotification(
                    id=f"mission_{m.id}",
                    type="mission",
                    title=f"Mission Complete: {m.title}",
                    message=f"You completed '{m.description}' and earned +{m.xp_reward} XP bonus.",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    icon=m.icon,
                )
            )

    # 4. Recent Solves
    for p in solved_records[:3]:
        q = catalog.get(p.question_id)
        if q:
            title = q["question"][:55] + "..." if len(q["question"]) > 55 else q["question"]
            notifications.append(
                PracticeNotification(
                    id=f"solve_{p.question_id}_{int(p.last_attempted_at.timestamp())}",
                    type="xp_gain",
                    title="Question Solved",
                    message=f"Solved '{title}' in {q['topic']}.",
                    timestamp=p.last_attempted_at.isoformat(),
                    icon="✓",
                )
            )

    # 5. Achievements
    for a in achievements:
        if a.unlocked:
            notifications.append(
                PracticeNotification(
                    id=f"ach_{a.id}",
                    type="achievement",
                    title=f"Achievement Unlocked: {a.title}",
                    message=a.description,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    icon=a.icon,
                )
            )

    return notifications


async def get_user_practice_stats(
    db: AsyncSession,
    user_id: UUID,
) -> PracticeStatsResponse:
    catalog = await load_all_platform_questions(db)

    stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    total_xp, xp_stats = _calculate_xp_from_records(catalog, records)
    mastery_stats = _evaluate_mastery_from_records(catalog, records)
    streak_stats = _calculate_streak_from_records(records)
    missions = _evaluate_missions_from_records(catalog, records)

    # Real PostgreSQL-backed achievements
    from app.modules.achievements.service import evaluate_user_achievements
    db_achievements, _ = await evaluate_user_achievements(db, user_id, catalog)
    achievements = [
        PracticeAchievement(
            id=a.id,
            title=a.name,
            description=a.description,
            icon=a.icon,
            unlocked=a.unlocked,
            progress=f"{a.current_progress} / {a.target_progress}",
            category=a.category.lower(),
        )
        for a in db_achievements
    ]

    notifications = _generate_notifications(
        catalog, records, xp_stats, streak_stats, missions, achievements
    )

    return PracticeStatsResponse(
        xp=xp_stats,
        mastery=mastery_stats,
        streak=streak_stats,
        missions=missions,
        achievements=achievements,
        notifications=notifications,
    )

