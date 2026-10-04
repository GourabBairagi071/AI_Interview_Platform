from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.achievements.model import AchievementDefinition, UserAchievement
from app.modules.achievements.schema import (
    AchievementDetailResponse,
    AchievementItem,
    AchievementListResponse,
    AchievementSummaryResponse,
    CategoryProgress,
)
from app.modules.interview.model import Interview
from app.modules.practice.model import PracticeProgress
from app.modules.practice.service import (
    _calculate_streak_from_records,
    _calculate_xp_from_records,
    _evaluate_missions_from_records,
    load_all_platform_questions,
)


CANONICAL_ACHIEVEMENTS = [
    # 1. PRACTICE
    {
        "id": "first_solve",
        "name": "First Step",
        "description": "Solve your first practice question in any technology",
        "category": "Practice",
        "icon": "🎯",
        "rarity": "Common",
        "xp_reward": 25,
        "target_value": 1,
        "sort_order": 1,
        "metric_key": "total_solved",
    },
    {
        "id": "solve_10",
        "name": "Practice Explorer",
        "description": "Solve 10 practice questions across any subjects",
        "category": "Practice",
        "icon": "📚",
        "rarity": "Common",
        "xp_reward": 50,
        "target_value": 10,
        "sort_order": 2,
        "metric_key": "total_solved",
    },
    {
        "id": "solve_50",
        "name": "Half Century",
        "description": "Solve 50 practice questions in the platform question bank",
        "category": "Practice",
        "icon": "🏅",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 50,
        "sort_order": 3,
        "metric_key": "total_solved",
    },
    {
        "id": "solve_100",
        "name": "Centurion Solver",
        "description": "Solve 100 practice questions",
        "category": "Practice",
        "icon": "👑",
        "rarity": "Epic",
        "xp_reward": 200,
        "target_value": 100,
        "sort_order": 4,
        "metric_key": "total_solved",
    },
    {
        "id": "solve_250",
        "name": "Problem Connoisseur",
        "description": "Solve 250 practice questions",
        "category": "Practice",
        "icon": "💎",
        "rarity": "Epic",
        "xp_reward": 350,
        "target_value": 250,
        "sort_order": 5,
        "metric_key": "total_solved",
    },
    {
        "id": "solve_500",
        "name": "Practice Grandmaster",
        "description": "Solve 500 practice questions from the canonical repository",
        "category": "Practice",
        "icon": "🏆",
        "rarity": "Legendary",
        "xp_reward": 500,
        "target_value": 500,
        "sort_order": 6,
        "metric_key": "total_solved",
    },

    # 2. CONSISTENCY
    {
        "id": "streak_3",
        "name": "Consistent Practitioner",
        "description": "Maintain a 3-day consecutive practice streak",
        "category": "Consistency",
        "icon": "🔥",
        "rarity": "Common",
        "xp_reward": 30,
        "target_value": 3,
        "sort_order": 10,
        "metric_key": "streak_days",
    },
    {
        "id": "streak_7",
        "name": "Week of Dedication",
        "description": "Maintain a 7-day consecutive practice streak",
        "category": "Consistency",
        "icon": "⚡",
        "rarity": "Rare",
        "xp_reward": 75,
        "target_value": 7,
        "sort_order": 11,
        "metric_key": "streak_days",
    },
    {
        "id": "streak_14",
        "name": "Fortnight Warrior",
        "description": "Maintain a 14-day consecutive practice streak",
        "category": "Consistency",
        "icon": "🛡️",
        "rarity": "Epic",
        "xp_reward": 150,
        "target_value": 14,
        "sort_order": 12,
        "metric_key": "streak_days",
    },
    {
        "id": "streak_30",
        "name": "Iron Discipline",
        "description": "Maintain a 30-day consecutive practice streak",
        "category": "Consistency",
        "icon": "🔱",
        "rarity": "Legendary",
        "xp_reward": 300,
        "target_value": 30,
        "sort_order": 13,
        "metric_key": "streak_days",
    },
    {
        "id": "daily_mission_1",
        "name": "Mission Cadet",
        "description": "Complete your first daily practice quest",
        "category": "Consistency",
        "icon": "🎯",
        "rarity": "Common",
        "xp_reward": 25,
        "target_value": 1,
        "sort_order": 14,
        "metric_key": "daily_missions_completed",
    },
    {
        "id": "daily_all",
        "name": "Daily Achiever",
        "description": "Complete all 3 daily practice missions in a single day",
        "category": "Consistency",
        "icon": "🌟",
        "rarity": "Rare",
        "xp_reward": 50,
        "target_value": 3,
        "sort_order": 15,
        "metric_key": "daily_missions_completed",
    },

    # 3. MASTERY
    {
        "id": "topic_master_1",
        "name": "Subject Initiate",
        "description": "Achieve 80%+ mastery in at least 1 topic",
        "category": "Mastery",
        "icon": "🧠",
        "rarity": "Rare",
        "xp_reward": 50,
        "target_value": 1,
        "sort_order": 20,
        "metric_key": "mastered_topics",
    },
    {
        "id": "topic_master_3",
        "name": "Polymath",
        "description": "Achieve 80%+ mastery in at least 3 distinct topics",
        "category": "Mastery",
        "icon": "🧭",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 3,
        "sort_order": 21,
        "metric_key": "mastered_topics",
    },
    {
        "id": "topic_master_5",
        "name": "Domain Specialist",
        "description": "Achieve 80%+ mastery in at least 5 distinct topics",
        "category": "Mastery",
        "icon": "🎓",
        "rarity": "Epic",
        "xp_reward": 200,
        "target_value": 5,
        "sort_order": 22,
        "metric_key": "mastered_topics",
    },
    {
        "id": "topic_master_10",
        "name": "Master of Crafts",
        "description": "Achieve 80%+ mastery in 10 or more topics",
        "category": "Mastery",
        "icon": "🪐",
        "rarity": "Legendary",
        "xp_reward": 400,
        "target_value": 10,
        "sort_order": 23,
        "metric_key": "mastered_topics",
    },

    # 4. DIFFICULTY
    {
        "id": "diff_easy_10",
        "name": "Fundamentalist",
        "description": "Solve 10 Easy difficulty questions",
        "category": "Difficulty",
        "icon": "🟢",
        "rarity": "Common",
        "xp_reward": 40,
        "target_value": 10,
        "sort_order": 30,
        "metric_key": "easy_solved",
    },
    {
        "id": "diff_med_5",
        "name": "Bridge Builder",
        "description": "Solve 5 Medium difficulty questions",
        "category": "Difficulty",
        "icon": "🟡",
        "rarity": "Common",
        "xp_reward": 50,
        "target_value": 5,
        "sort_order": 31,
        "metric_key": "med_solved",
    },
    {
        "id": "diff_med_25",
        "name": "Core Competent",
        "description": "Solve 25 Medium difficulty questions",
        "category": "Difficulty",
        "icon": "🔶",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 25,
        "sort_order": 32,
        "metric_key": "med_solved",
    },
    {
        "id": "diff_hard_1",
        "name": "Tough Nut",
        "description": "Solve your first Hard difficulty interview question",
        "category": "Difficulty",
        "icon": "🔴",
        "rarity": "Rare",
        "xp_reward": 50,
        "target_value": 1,
        "sort_order": 33,
        "metric_key": "hard_solved",
    },
    {
        "id": "diff_hard_10",
        "name": "Hardcore Solver",
        "description": "Solve 10 Hard difficulty questions",
        "category": "Difficulty",
        "icon": "🛑",
        "rarity": "Epic",
        "xp_reward": 150,
        "target_value": 10,
        "sort_order": 34,
        "metric_key": "hard_solved",
    },
    {
        "id": "diff_hard_25",
        "name": "Titan of Algorithms",
        "description": "Solve 25 Hard difficulty questions",
        "category": "Difficulty",
        "icon": "💥",
        "rarity": "Legendary",
        "xp_reward": 300,
        "target_value": 25,
        "sort_order": 35,
        "metric_key": "hard_solved",
    },

    # 5. TECHNOLOGY
    {
        "id": "multi_topic",
        "name": "Tech Explorer",
        "description": "Solve questions across 3 or more distinct technologies",
        "category": "Technology",
        "icon": "🌐",
        "rarity": "Common",
        "xp_reward": 50,
        "target_value": 3,
        "sort_order": 40,
        "metric_key": "technologies_count",
    },
    {
        "id": "tech_explorer_5",
        "name": "Tech Polyglot",
        "description": "Solve questions across 5 or more distinct technologies",
        "category": "Technology",
        "icon": "🚀",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 5,
        "sort_order": 41,
        "metric_key": "technologies_count",
    },
    {
        "id": "tech_explorer_10",
        "name": "Full Spectrum Engineer",
        "description": "Solve questions across 10 or more distinct technologies",
        "category": "Technology",
        "icon": "🌌",
        "rarity": "Epic",
        "xp_reward": 250,
        "target_value": 10,
        "sort_order": 42,
        "metric_key": "technologies_count",
    },
    {
        "id": "tech_depth_20",
        "name": "Specialized Deep-Dive",
        "description": "Solve 20 or more questions within a single technology",
        "category": "Technology",
        "icon": "🔬",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 20,
        "sort_order": 43,
        "metric_key": "max_tech_depth",
    },

    # 6. PROBLEM SOLVING
    {
        "id": "detailed_solution_5",
        "name": "Articulate Thinker",
        "description": "Save 5 detailed answers of 50+ characters with your solutions",
        "category": "Problem Solving",
        "icon": "📝",
        "rarity": "Common",
        "xp_reward": 50,
        "target_value": 5,
        "sort_order": 50,
        "metric_key": "detailed_answers",
    },
    {
        "id": "first_attempt_10",
        "name": "First-Shot Prodigy",
        "description": "Solve 10 questions on the very first attempt",
        "category": "Problem Solving",
        "icon": "🎯",
        "rarity": "Rare",
        "xp_reward": 75,
        "target_value": 10,
        "sort_order": 51,
        "metric_key": "first_attempt_solved",
    },
    {
        "id": "bookmark_5",
        "name": "Curator",
        "description": "Bookmark 5 questions for deliberate revision",
        "category": "Problem Solving",
        "icon": "🔖",
        "rarity": "Common",
        "xp_reward": 25,
        "target_value": 5,
        "sort_order": 52,
        "metric_key": "bookmarked_count",
    },

    # 7. INTERVIEW
    {
        "id": "mock_complete_1",
        "name": "Interview Debut",
        "description": "Complete your first AI mock interview simulation",
        "category": "Interview",
        "icon": "🎤",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 1,
        "sort_order": 60,
        "metric_key": "completed_interviews",
    },
    {
        "id": "mock_complete_5",
        "name": "Interview Veteran",
        "description": "Complete 5 AI mock interview sessions",
        "category": "Interview",
        "icon": "💼",
        "rarity": "Epic",
        "xp_reward": 200,
        "target_value": 5,
        "sort_order": 61,
        "metric_key": "completed_interviews",
    },
    {
        "id": "mock_high_score",
        "name": "Top Performer",
        "description": "Achieve a score of 80% or higher on an interview session",
        "category": "Interview",
        "icon": "🌟",
        "rarity": "Epic",
        "xp_reward": 150,
        "target_value": 80,
        "sort_order": 62,
        "metric_key": "max_interview_score",
    },

    # 8. MILESTONES
    {
        "id": "xp_100",
        "name": "Century Club",
        "description": "Accumulate 100+ Total Practice XP points",
        "category": "Milestones",
        "icon": "⭐",
        "rarity": "Common",
        "xp_reward": 50,
        "target_value": 100,
        "sort_order": 70,
        "metric_key": "total_xp",
    },
    {
        "id": "xp_500",
        "name": "XP Enthusiast",
        "description": "Accumulate 500+ Total Practice XP points",
        "category": "Milestones",
        "icon": "✨",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 500,
        "sort_order": 71,
        "metric_key": "total_xp",
    },
    {
        "id": "xp_1000",
        "name": "Kilopoint Leader",
        "description": "Accumulate 1,000+ Total Practice XP points",
        "category": "Milestones",
        "icon": "🌠",
        "rarity": "Epic",
        "xp_reward": 200,
        "target_value": 1000,
        "sort_order": 72,
        "metric_key": "total_xp",
    },
    {
        "id": "level_3",
        "name": "Technical Specialist",
        "description": "Attain Level 3 rank in Question Practice",
        "category": "Milestones",
        "icon": "🎖️",
        "rarity": "Rare",
        "xp_reward": 100,
        "target_value": 3,
        "sort_order": 73,
        "metric_key": "level",
    },
    {
        "id": "level_5",
        "name": "Staff Architect",
        "description": "Reach the prestigious Level 5 Staff Architect rank",
        "category": "Milestones",
        "icon": "👑",
        "rarity": "Legendary",
        "xp_reward": 300,
        "target_value": 5,
        "sort_order": 74,
        "metric_key": "level",
    },
]


async def ensure_achievement_definitions(db: AsyncSession) -> list[AchievementDefinition]:
    """
    Ensures all canonical achievement definitions exist in the database.
    Idempotent and safe to run on startup or evaluation.
    """
    stmt = select(AchievementDefinition)
    res = await db.execute(stmt)
    existing = {d.id: d for d in res.scalars().all()}

    now = datetime.now(timezone.utc)
    added_any = False

    for item in CANONICAL_ACHIEVEMENTS:
        aid = item["id"]
        if aid not in existing:
            defn = AchievementDefinition(
                id=aid,
                name=item["name"],
                description=item["description"],
                category=item["category"],
                icon=item["icon"],
                rarity=item["rarity"],
                xp_reward=item["xp_reward"],
                target_value=item["target_value"],
                is_active=True,
                sort_order=item["sort_order"],
                requirement_metadata={"metric_key": item["metric_key"]},
                created_at=now,
                updated_at=now,
            )
            db.add(defn)
            existing[aid] = defn
            added_any = True

    if added_any:
        await db.commit()

    return sorted(list(existing.values()), key=lambda d: d.sort_order)


async def calculate_user_metrics(
    db: AsyncSession,
    user_id: UUID,
    catalog: dict[str, dict] | None = None,
) -> dict:
    """
    Aggregates user metrics across practice and interview activity in minimal queries.
    """
    if catalog is None:
        catalog = await load_all_platform_questions(db)

    # 1. Practice progress records
    stmt_prog = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
    res_prog = await db.execute(stmt_prog)
    records = list(res_prog.scalars().all())

    solved_records = [p for p in records if p.solved]
    total_solved = len(solved_records)

    easy_solved = 0
    med_solved = 0
    hard_solved = 0
    first_attempt_solved = 0
    detailed_answers = 0
    bookmarked_count = sum(1 for p in records if p.bookmarked)

    tech_counts: dict[str, int] = defaultdict(int)
    topic_counts: dict[str, int] = defaultdict(int)

    for p in solved_records:
        if p.attempts == 1:
            first_attempt_solved += 1
        if p.last_answer and len(p.last_answer.strip()) >= 50:
            detailed_answers += 1

        q = catalog.get(p.question_id)
        if q:
            diff = q.get("difficulty", "Medium").lower()
            if diff == "easy":
                easy_solved += 1
            elif diff == "hard":
                hard_solved += 1
            else:
                med_solved += 1

            tech = q.get("technology") or "General"
            top = q.get("topic") or "General"
            tech_counts[tech] += 1
            topic_counts[top] += 1

    technologies_count = len(tech_counts)
    max_tech_depth = max(tech_counts.values()) if tech_counts else 0

    # Topic mastery (topics where user solved >= 80% of topic questions)
    topic_total_q: dict[str, int] = defaultdict(int)
    for q in catalog.values():
        top = q.get("topic") or "General"
        topic_total_q[top] += 1

    mastered_topics = 0
    for top, solved_c in topic_counts.items():
        total_t = topic_total_q.get(top, 1)
        if total_t > 0 and (solved_c / total_t) >= 0.8:
            mastered_topics += 1

    # Streaks, Missions, and XP
    streak = _calculate_streak_from_records(records)
    streak_days = max(streak.current_streak, streak.longest_streak)

    missions = _evaluate_missions_from_records(catalog, records)
    daily_missions_completed = sum(1 for m in missions if m.completed)

    total_xp, xp_stats = _calculate_xp_from_records(catalog, records)

    # 2. Interviews
    stmt_int = select(Interview).where(
        Interview.user_id == user_id,
        Interview.status == "completed",
    )
    res_int = await db.execute(stmt_int)
    completed_interviews_list = list(res_int.scalars().all())
    completed_interviews = len(completed_interviews_list)

    max_interview_score = 0
    for iv in completed_interviews_list:
        if iv.score is not None:
            max_interview_score = max(max_interview_score, int(round(iv.score)))

    return {
        "total_solved": total_solved,
        "easy_solved": easy_solved,
        "med_solved": med_solved,
        "hard_solved": hard_solved,
        "first_attempt_solved": first_attempt_solved,
        "detailed_answers": detailed_answers,
        "bookmarked_count": bookmarked_count,
        "technologies_count": technologies_count,
        "max_tech_depth": max_tech_depth,
        "mastered_topics": mastered_topics,
        "streak_days": streak_days,
        "daily_missions_completed": daily_missions_completed,
        "total_xp": total_xp,
        "level": xp_stats.level,
        "completed_interviews": completed_interviews,
        "max_interview_score": max_interview_score,
    }


async def evaluate_user_achievements(
    db: AsyncSession,
    user_id: UUID,
    catalog: dict[str, dict] | None = None,
) -> tuple[list[AchievementItem], list[AchievementItem]]:
    """
    Evaluates achievement unlock criteria for the user.
    Deterministic, idempotent, transaction-safe, user-scoped.
    Returns: (all_achievements, newly_unlocked_achievements)
    """
    definitions = await ensure_achievement_definitions(db)
    metrics = await calculate_user_metrics(db=db, user_id=user_id, catalog=catalog)

    stmt_user = select(UserAchievement).where(UserAchievement.user_id == user_id)
    res_user = await db.execute(stmt_user)
    existing_user_ach = {a.achievement_id: a for a in res_user.scalars().all()}

    now = datetime.now(timezone.utc)
    newly_unlocked_items: list[AchievementItem] = []
    all_items: list[AchievementItem] = []

    for defn in definitions:
        metric_key = defn.requirement_metadata.get("metric_key", "total_solved")
        metric_val = metrics.get(metric_key, 0)
        target = defn.target_value
        progress = min(metric_val, target)
        pct = round((progress / target) * 100.0, 1) if target > 0 else 100.0
        should_unlock = progress >= target

        user_ach = existing_user_ach.get(defn.id)

        if user_ach is None:
            user_ach = UserAchievement(
                user_id=user_id,
                achievement_id=defn.id,
                current_progress=progress,
                target_progress=target,
                unlocked=should_unlock,
                unlocked_at=now if should_unlock else None,
                created_at=now,
                updated_at=now,
            )
            db.add(user_ach)
            existing_user_ach[defn.id] = user_ach
            if should_unlock:
                newly_unlocked_items.append(
                    AchievementItem(
                        id=defn.id,
                        name=defn.name,
                        description=defn.description,
                        category=defn.category,
                        icon=defn.icon,
                        rarity=defn.rarity,
                        xp_reward=defn.xp_reward,
                        current_progress=progress,
                        target_progress=target,
                        progress_percentage=pct,
                        unlocked=True,
                        unlocked_at=now.isoformat(),
                        requirement_description=defn.description,
                    )
                )
        else:
            # Update progress
            user_ach.current_progress = progress
            user_ach.target_progress = target
            user_ach.updated_at = now

            if not user_ach.unlocked and should_unlock:
                user_ach.unlocked = True
                user_ach.unlocked_at = now
                newly_unlocked_items.append(
                    AchievementItem(
                        id=defn.id,
                        name=defn.name,
                        description=defn.description,
                        category=defn.category,
                        icon=defn.icon,
                        rarity=defn.rarity,
                        xp_reward=defn.xp_reward,
                        current_progress=progress,
                        target_progress=target,
                        progress_percentage=pct,
                        unlocked=True,
                        unlocked_at=now.isoformat(),
                        requirement_description=defn.description,
                    )
                )

        all_items.append(
            AchievementItem(
                id=defn.id,
                name=defn.name,
                description=defn.description,
                category=defn.category,
                icon=defn.icon,
                rarity=defn.rarity,
                xp_reward=defn.xp_reward,
                current_progress=user_ach.current_progress,
                target_progress=user_ach.target_progress,
                progress_percentage=round((user_ach.current_progress / user_ach.target_progress) * 100.0, 1),
                unlocked=user_ach.unlocked,
                unlocked_at=user_ach.unlocked_at.isoformat() if user_ach.unlocked_at else None,
                requirement_description=defn.description,
            )
        )

    # Persist real notifications for newly unlocked achievements
    if newly_unlocked_items:
        try:
            from app.modules.notifications.service import NotificationService
            from app.modules.notifications.schema import NotificationType
            for ach in newly_unlocked_items:
                event_key = f"achievement_unlocked:{user_id}:{ach.id}"
                await NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    type=NotificationType.ACHIEVEMENT_UNLOCKED.value,
                    title=f"Achievement Unlocked: {ach.name}",
                    message=f"You unlocked '{ach.name}'! {ach.description} (+{ach.xp_reward} XP)",
                    icon=ach.icon or "🏆",
                    event_key=event_key,
                    metadata={
                        "achievement_id": ach.id,
                        "category": ach.category,
                        "xp_reward": ach.xp_reward,
                        "rarity": ach.rarity,
                    },
                    action_url="/achievements",
                    priority="high",
                    commit=False,
                )
        except Exception as e:
            logger.warning("Failed to create achievement notifications: %s", e)

    await db.commit()

    return all_items, newly_unlocked_items


async def get_user_achievements_list(
    db: AsyncSession,
    user_id: UUID,
    category: str | None = None,
) -> AchievementListResponse:
    """
    Returns the complete achievement catalog with the authenticated user's state.
    """
    all_items, _ = await evaluate_user_achievements(db, user_id)

    if category and category.lower() != "all":
        cat_clean = category.strip().lower()
        all_items = [a for a in all_items if a.category.lower() == cat_clean]

    # Sort: unlocked first (most recently unlocked top), then by progress % descending, then by target
    all_items.sort(
        key=lambda a: (
            not a.unlocked,
            -a.progress_percentage,
            a.id,
        )
    )

    unlocked_count = sum(1 for a in all_items if a.unlocked)

    return AchievementListResponse(
        achievements=all_items,
        total=len(all_items),
        unlocked_count=unlocked_count,
    )


async def get_user_achievements_summary(
    db: AsyncSession,
    user_id: UUID,
) -> AchievementSummaryResponse:
    """
    Returns high-level statistics and category breakdowns for achievements.
    """
    all_items, _ = await evaluate_user_achievements(db, user_id)

    total_ach = len(all_items)
    unlocked_items = [a for a in all_items if a.unlocked]
    unlocked_count = len(unlocked_items)
    locked_count = total_ach - unlocked_count

    total_xp_earned = sum(a.xp_reward for a in unlocked_items)
    pct = round((unlocked_count / total_ach) * 100.0, 1) if total_ach > 0 else 0.0

    # Sort unlocked items by unlock date descending
    unlocked_items.sort(
        key=lambda a: a.unlocked_at or "",
        reverse=True,
    )
    recent_unlocks = unlocked_items[:5]

    # Categories breakdown
    cat_map: dict[str, list[AchievementItem]] = defaultdict(list)
    for a in all_items:
        cat_map[a.category].append(a)

    categories: list[CategoryProgress] = []
    for cat_name, cat_items in cat_map.items():
        c_tot = len(cat_items)
        c_unl = sum(1 for a in cat_items if a.unlocked)
        c_pct = round((c_unl / c_tot) * 100.0, 1) if c_tot > 0 else 0.0
        categories.append(
            CategoryProgress(
                category=cat_name,
                total=c_tot,
                unlocked=c_unl,
                percentage=c_pct,
            )
        )

    categories.sort(key=lambda c: c.category)

    return AchievementSummaryResponse(
        total_achievements=total_ach,
        unlocked_count=unlocked_count,
        locked_count=locked_count,
        total_xp_earned=total_xp_earned,
        completion_percentage=pct,
        recent_unlocks=recent_unlocks,
        categories=categories,
    )


async def get_achievement_detail(
    db: AsyncSession,
    user_id: UUID,
    achievement_id: str,
) -> AchievementDetailResponse:
    """
    Returns detailed achievement information for a specific achievement ID.
    """
    all_items, _ = await evaluate_user_achievements(db, user_id)
    matching = [a for a in all_items if a.id == achievement_id]
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Achievement '{achievement_id}' not found.",
        )

    metrics = await calculate_user_metrics(db=db, user_id=user_id)

    return AchievementDetailResponse(
        achievement=matching[0],
        related_metrics=metrics,
    )
