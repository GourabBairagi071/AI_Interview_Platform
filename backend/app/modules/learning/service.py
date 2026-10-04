from datetime import date, datetime, timedelta, timezone
import json
import logging
from typing import Any
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.model import User, UserProfile
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.interview.model import Interview
from app.modules.learning.evaluator import (
    DEFAULT_THRESHOLDS,
    evaluate_user_skills,
    sync_and_persist_skill_performances,
)
from app.modules.learning.model import (
    DailyPracticePlan,
    LearningProfile,
    LearningRecommendation,
    LearningResource,
    LearningRoadmap,
    SkillPerformance,
    WeeklyGoal,
)
from app.modules.learning.normalizer import normalize_skill_name
from app.modules.learning.seed_resources import seed_learning_resources_if_needed
from app.modules.rag.retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class LearningService:
    @staticmethod
    async def get_or_create_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> LearningProfile:
        res = await db.execute(
            select(LearningProfile).where(LearningProfile.user_id == user_id)
        )
        profile = res.scalar_one_or_none()
        if not profile:
            # Check user headline or resume if available
            prof_res = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            u_prof = prof_res.scalar_one_or_none()
            default_role = u_prof.headline if u_prof and u_prof.headline else "Full Stack Developer"

            profile = LearningProfile(
                user_id=user_id,
                target_role=default_role,
                target_level="Mid-Level",
                overall_readiness_score=None,
                hours_per_week=10,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        target_role: str | None = None,
        target_level: str | None = None,
        hours_per_week: int | None = None,
    ) -> LearningProfile:
        profile = await LearningService.get_or_create_profile(db, user_id)
        if target_role:
            profile.target_role = target_role
        if target_level:
            profile.target_level = target_level
        if hours_per_week is not None:
            profile.hours_per_week = hours_per_week

        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def get_user_skills(
        db: AsyncSession,
        user_id: uuid.UUID,
        force_sync: bool = False,
    ) -> list[SkillPerformance]:
        # Seed resources if needed
        await seed_learning_resources_if_needed(db)

        if force_sync:
            await sync_and_persist_skill_performances(db, user_id)

        res = await db.execute(
            select(SkillPerformance)
            .where(SkillPerformance.user_id == user_id)
            .order_by(SkillPerformance.combined_score.asc().nulls_last())
        )
        skills = list(res.scalars().all())

        if not skills and not force_sync:
            # Sync once if empty
            skills = await sync_and_persist_skill_performances(db, user_id)

        return skills

    @staticmethod
    async def get_weak_topics(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        skills = await LearningService.get_user_skills(db, user_id)
        weak_list: list[dict[str, Any]] = []

        for sk in skills:
            if sk.status in ("weak", "needs_practice"):
                priority = "high" if sk.status == "weak" else "medium"
                weak_list.append({
                    "topic": sk.canonical_skill,
                    "category": sk.category,
                    "combined_score": sk.combined_score,
                    "status": sk.status,
                    "confidence": sk.confidence,
                    "attempts": sk.total_attempts,
                    "priority": priority,
                    "reason": (
                        f"Current evaluated score is {sk.combined_score}/100 across {sk.total_attempts} attempt{'s' if sk.total_attempts != 1 else ''}."
                        if sk.combined_score is not None
                        else "Identified in required skill profile without completed assessments."
                    ),
                    "recommended_action": (
                        f"Practice foundational questions and coding challenges in {sk.canonical_skill}."
                    ),
                })

        # Sort: High priority first, then lowest score
        weak_list.sort(
            key=lambda x: (
                0 if x["priority"] == "high" else 1,
                x["combined_score"] if x["combined_score"] is not None else 999,
            )
        )
        return weak_list

    @staticmethod
    async def generate_or_get_roadmap(
        db: AsyncSession,
        user_id: uuid.UUID,
        target_role: str | None = None,
        target_level: str | None = None,
        force_regenerate: bool = False,
    ) -> LearningRoadmap:
        profile = await LearningService.get_or_create_profile(db, user_id)
        if target_role:
            profile.target_role = target_role
        if target_level:
            profile.target_level = target_level

        if not force_regenerate:
            res = await db.execute(
                select(LearningRoadmap)
                .where(
                    LearningRoadmap.user_id == user_id,
                    LearningRoadmap.status == "active",
                )
                .order_by(LearningRoadmap.created_at.desc())
            )
            existing = res.scalar_one_or_none()
            if existing:
                return existing

        # Ensure skills are fresh
        await sync_and_persist_skill_performances(db, user_id)
        weak_topics = await LearningService.get_weak_topics(db, user_id)

        # Assemble prioritized topics
        priority_topics = [w["topic"] for w in weak_topics]
        if not priority_topics:
            priority_topics = [
                "Data Structures & Algorithms",
                "REST APIs",
                "System Design",
                "SQL",
            ]

        # Ensure at least 4 weeks
        role_label = profile.target_role or "Full Stack Developer"
        weeks_data = []

        for i in range(4):
            week_num = i + 1
            focus = priority_topics[i % len(priority_topics)]
            priority = "High" if i < 2 else "Medium"
            reason = (
                f"Addresses identified weakness in {focus} with technical exercises."
                if weak_topics and i < len(weak_topics)
                else f"Core milestone required for {role_label} competency."
            )

            items = [
                {
                    "id": f"w{week_num}_item1",
                    "title": f"Review {focus} Core Concepts & Official Docs",
                    "type": "study",
                    "topic": focus,
                    "is_completed": False,
                    "estimated_mins": 45,
                    "ref_link": None,
                },
                {
                    "id": f"w{week_num}_item2",
                    "title": f"Practice 3 {focus} Technical Interview Questions",
                    "type": "interview",
                    "topic": focus,
                    "is_completed": False,
                    "estimated_mins": 30,
                    "ref_link": "/practice",
                },
                {
                    "id": f"w{week_num}_item3",
                    "title": f"Solve 2 {focus} Coding Challenges",
                    "type": "coding",
                    "topic": focus,
                    "is_completed": False,
                    "estimated_mins": 60,
                    "ref_link": "/coding",
                },
            ]

            weeks_data.append({
                "week_number": week_num,
                "title": f"Week {week_num}: {focus} Mastery",
                "focus_topic": focus,
                "priority": priority,
                "reason": reason,
                "items": items,
            })

        # Archive old roadmaps
        old_res = await db.execute(
            select(LearningRoadmap).where(LearningRoadmap.user_id == user_id)
        )
        for old in old_res.scalars().all():
            old.status = "archived"

        new_roadmap = LearningRoadmap(
            user_id=user_id,
            target_role=role_label,
            title=f"Personalized {role_label} Preparation Roadmap",
            status="active",
            progress_percentage=0.0,
            weeks=weeks_data,
        )
        db.add(new_roadmap)
        await db.commit()
        await db.refresh(new_roadmap)
        return new_roadmap

    @staticmethod
    async def get_learning_resources(
        db: AsyncSession,
        user_id: uuid.UUID,
        topic: str | None = None,
        limit: int = 6,
    ) -> list[LearningResource]:
        await seed_learning_resources_if_needed(db)

        if topic and topic.strip():
            can_name, _ = normalize_skill_name(topic)
            res = await db.execute(
                select(LearningResource)
                .where(
                    (LearningResource.topic.ilike(f"%{topic}%"))
                    | (LearningResource.canonical_skill == can_name)
                )
                .limit(limit)
            )
            resources = list(res.scalars().all())
            if resources:
                return resources

        # Otherwise prioritize resources matching candidate's weak topics
        weak_topics = await LearningService.get_weak_topics(db, user_id)
        if weak_topics:
            target_skills = [w["topic"] for w in weak_topics[:3]]
            res = await db.execute(
                select(LearningResource)
                .where(LearningResource.canonical_skill.in_(target_skills))
                .limit(limit)
            )
            matched = list(res.scalars().all())
            if len(matched) >= limit:
                return matched[:limit]

        # Fallback to general high quality resources
        res = await db.execute(select(LearningResource).limit(limit))
        return list(res.scalars().all())

    @staticmethod
    async def get_interview_recommendations(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Uses Phase 10 SemanticRetriever to pull actual questions from the 5,738 bank
        for candidate's weak topics.
        """
        weak_topics = await LearningService.get_weak_topics(db, user_id)
        query_topic = weak_topics[0]["topic"] if weak_topics else "Data Structures"

        retriever = SemanticRetriever()
        try:
            questions = await retriever.retrieve(
                db=db,
                query=f"{query_topic} conceptual and scenario interview questions",
                topic=query_topic,
                limit=limit,
                min_similarity=0.10,
            )
            if questions:
                return [
                    {
                        "question_id": q.id,
                        "question": q.question,
                        "topic": q.topic,
                        "difficulty": q.difficulty,
                        "role": q.role,
                        "reason": f"Targeted practice to improve your {query_topic} evaluation score.",
                        "action_url": "/practice",
                    }
                    for q in questions
                ]
        except Exception as e:
            logger.warning(f"RAG interview recommendations fallback: {e}")

        # Deterministic fallback matching real canonical topics
        return [
            {
                "question_id": str(uuid.uuid4()),
                "question": f"Explain key design considerations and common pitfalls in {query_topic}.",
                "topic": query_topic,
                "difficulty": "Medium",
                "role": "Software Engineer",
                "reason": f"Targeted practice to strengthen {query_topic} comprehension.",
                "action_url": "/practice",
            }
        ]

    @staticmethod
    async def get_coding_recommendations(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Recommends unsolved challenges from the 1,000 problem Coding Arena
        targeting the candidate's weak algorithmic topics.
        """
        # Solved problem IDs
        subs_res = await db.execute(
            select(CodingSubmission.problem_id).where(
                CodingSubmission.user_id == user_id,
                CodingSubmission.status == "Accepted",
            )
        )
        solved_ids = set(subs_res.scalars().all())

        weak_topics = await LearningService.get_weak_topics(db, user_id)
        target_topic = weak_topics[0]["topic"] if weak_topics else None

        recommended_probs: list[CodingProblem] = []

        if target_topic:
            res = await db.execute(
                select(CodingProblem).where(
                    CodingProblem.topic.ilike(f"%{target_topic}%"),
                    CodingProblem.id.not_in(solved_ids) if solved_ids else True,
                ).limit(limit)
            )
            recommended_probs = list(res.scalars().all())

        if len(recommended_probs) < limit:
            remaining = limit - len(recommended_probs)
            existing_ids = {p.id for p in recommended_probs} | solved_ids
            res = await db.execute(
                select(CodingProblem).where(
                    CodingProblem.id.not_in(existing_ids) if existing_ids else True
                ).limit(remaining)
            )
            recommended_probs.extend(res.scalars().all())

        items = []
        for p in recommended_probs[:limit]:
            items.append({
                "problem_id": str(p.id),
                "title": p.title,
                "slug": p.slug,
                "difficulty": p.difficulty,
                "topic": p.topic,
                "reason": f"Recommended to reinforce {p.topic} problem solving.",
                "action_url": f"/coding/problem/{p.slug}",
            })

        return items

    @staticmethod
    async def get_or_create_daily_plan(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> DailyPracticePlan:
        today = date.today()
        res = await db.execute(
            select(DailyPracticePlan).where(
                DailyPracticePlan.user_id == user_id,
                DailyPracticePlan.plan_date == today,
            )
        )
        plan = res.scalar_one_or_none()
        if plan:
            return plan

        # Generate tailored daily plan
        weak_topics = await LearningService.get_weak_topics(db, user_id)
        focus_topic = weak_topics[0]["topic"] if weak_topics else "Data Structures & Algorithms"
        second_topic = weak_topics[1]["topic"] if len(weak_topics) > 1 else "REST APIs"

        items = [
            {
                "id": "task_1",
                "title": f"Study {focus_topic} core documentation & key patterns",
                "type": "study",
                "topic": focus_topic,
                "duration_mins": 25,
                "is_completed": False,
                "ref_type": "resource",
                "ref_id": None,
                "action_url": None,
            },
            {
                "id": "task_2",
                "title": f"Practice 2 interview questions on {focus_topic}",
                "type": "interview",
                "topic": focus_topic,
                "duration_mins": 20,
                "is_completed": False,
                "ref_type": "practice",
                "ref_id": None,
                "action_url": "/practice",
            },
            {
                "id": "task_3",
                "title": f"Solve 1 coding challenge on {second_topic}",
                "type": "coding",
                "topic": second_topic,
                "duration_mins": 30,
                "is_completed": False,
                "ref_type": "coding",
                "ref_id": None,
                "action_url": "/coding",
            },
            {
                "id": "task_4",
                "title": f"Quick 10-minute flash revision of {focus_topic} pitfalls",
                "type": "revision",
                "topic": focus_topic,
                "duration_mins": 10,
                "is_completed": False,
                "ref_type": "revision",
                "ref_id": None,
                "action_url": None,
            },
        ]

        plan = DailyPracticePlan(
            user_id=user_id,
            plan_date=today,
            items=items,
            is_completed=False,
            completed_at=None,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def complete_daily_task(
        db: AsyncSession,
        user_id: uuid.UUID,
        task_id: str,
    ) -> DailyPracticePlan:
        plan = await LearningService.get_or_create_daily_plan(db, user_id)
        items = list(plan.items or [])
        found = False

        for it in items:
            if it.get("id") == task_id:
                it["is_completed"] = not it.get("is_completed", False)
                found = True
                break

        if found:
            from sqlalchemy.orm.attributes import flag_modified
            plan.items = [dict(it) for it in items]
            flag_modified(plan, "items")
            all_done = all(it.get("is_completed", False) for it in plan.items)
            plan.is_completed = all_done
            plan.completed_at = datetime.now(timezone.utc) if all_done else None
            await db.commit()
            await db.refresh(plan)

        return plan

    @staticmethod
    async def get_or_create_weekly_goals(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[WeeklyGoal]:
        today = date.today()
        # Monday of current week
        week_start = today - timedelta(days=today.weekday())

        res = await db.execute(
            select(WeeklyGoal).where(
                WeeklyGoal.user_id == user_id,
                WeeklyGoal.week_start_date == week_start,
            )
        )
        goals = list(res.scalars().all())
        if goals:
            return goals

        # Compute actual counts from this week
        deadline = datetime(week_start.year, week_start.month, week_start.day, 23, 59, 59, tzinfo=timezone.utc) + timedelta(days=6)

        default_goals = [
            WeeklyGoal(
                user_id=user_id,
                week_start_date=week_start,
                title="Complete 5 Technical Interview Questions",
                goal_type="interview",
                target_count=5,
                completed_count=0,
                deadline=deadline,
                status="in_progress",
            ),
            WeeklyGoal(
                user_id=user_id,
                week_start_date=week_start,
                title="Solve 4 Algorithmic Coding Challenges",
                goal_type="coding",
                target_count=4,
                completed_count=0,
                deadline=deadline,
                status="in_progress",
            ),
            WeeklyGoal(
                user_id=user_id,
                week_start_date=week_start,
                title="Complete 3 Targeted Weakness Learning Modules",
                goal_type="learning",
                target_count=3,
                completed_count=0,
                deadline=deadline,
                status="in_progress",
            ),
            WeeklyGoal(
                user_id=user_id,
                week_start_date=week_start,
                title="Take 1 Complete AI Mock Interview",
                goal_type="interview",
                target_count=1,
                completed_count=0,
                deadline=deadline,
                status="in_progress",
            ),
        ]

        for g in default_goals:
            db.add(g)

        await db.commit()
        for g in default_goals:
            await db.refresh(g)

        return default_goals

    @staticmethod
    async def complete_weekly_goal_step(
        db: AsyncSession,
        user_id: uuid.UUID,
        goal_id: uuid.UUID,
    ) -> WeeklyGoal | None:
        res = await db.execute(
            select(WeeklyGoal).where(
                WeeklyGoal.id == goal_id,
                WeeklyGoal.user_id == user_id,
            )
        )
        goal = res.scalar_one_or_none()
        if not goal:
            return None

        goal.completed_count = min(goal.target_count, goal.completed_count + 1)
        if goal.completed_count >= goal.target_count:
            goal.status = "completed"

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def get_learning_progress(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        skills = await LearningService.get_user_skills(db, user_id)
        strong_count = sum(1 for s in skills if s.status == "strong")
        needs_practice_count = sum(1 for s in skills if s.status == "needs_practice")
        weak_count = sum(1 for s in skills if s.status == "weak")

        # Readiness formula
        assessed = [s.combined_score for s in skills if s.combined_score is not None]
        if assessed:
            overall_readiness = round(sum(assessed) / len(assessed), 1)
        else:
            overall_readiness = 50.0  # Base neutral readiness when unassessed

        # Roadmap progress
        rm = await LearningService.generate_or_get_roadmap(db, user_id)
        rm_pct = rm.progress_percentage if rm else 0.0

        # Daily plan status
        plan = await LearningService.get_or_create_daily_plan(db, user_id)

        # Weekly goals
        goals = await LearningService.get_or_create_weekly_goals(db, user_id)
        total_target = sum(g.target_count for g in goals)
        total_completed = sum(g.completed_count for g in goals)
        goals_pct = round((total_completed / total_target) * 100.0, 1) if total_target > 0 else 0.0

        # Skills trend
        trend = []
        for s in skills:
            history = s.score_history or []
            initial_score = history[0].get("score") if history else s.combined_score
            delta = (
                round(s.combined_score - initial_score, 1)
                if s.combined_score is not None and initial_score is not None
                else 0.0
            )
            trend.append({
                "canonical_skill": s.canonical_skill,
                "current_score": s.combined_score,
                "initial_score": initial_score,
                "delta": delta,
                "status": s.status,
                "attempts": s.total_attempts,
            })

        # Summary message
        if weak_count > 0:
            summary = f"Detected {weak_count} priority topic{'s' if weak_count != 1 else ''} needing reinforcement. Focus on recommended practice today."
        elif strong_count > 0:
            summary = "Great consistency! Keep practicing to maintain high performance across your technical skills."
        else:
            summary = "Complete an interview or coding challenge to generate your detailed personalized skill roadmap."

        return {
            "overall_readiness": overall_readiness,
            "total_skills_assessed": len(skills),
            "strong_skills_count": strong_count,
            "needs_practice_count": needs_practice_count,
            "weak_skills_count": weak_count,
            "roadmap_progress_pct": rm_pct,
            "daily_plan_completed": plan.is_completed,
            "weekly_goals_completed_pct": goals_pct,
            "skills_trend": trend,
            "summary_message": summary,
        }
