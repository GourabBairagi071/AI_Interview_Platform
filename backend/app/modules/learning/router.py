from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.learning.schema import (
    ConsolidatedRecommendationsResponse,
    DailyPracticePlanResponse,
    LearningProfileResponse,
    LearningProfileUpdateRequest,
    LearningProgressResponse,
    LearningResourceItem,
    LearningRoadmapResponse,
    RoadmapGenerateRequest,
    SkillPerformanceItem,
    WeakTopicItem,
    WeeklyGoalItem,
)
from app.modules.learning.service import LearningService

router = APIRouter(
    prefix="/learning",
    tags=["Personalized Learning & Recommendations"],
)


# -------------------------------------------------------------
# 1. Learning Profile
# -------------------------------------------------------------
@router.get(
    "/profile",
    response_model=LearningProfileResponse,
    summary="Get candidate's personalized learning profile",
)
async def get_learning_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await LearningService.get_or_create_profile(db, current_user.id)
    return profile


@router.put(
    "/profile",
    response_model=LearningProfileResponse,
    summary="Update candidate's target role or study hours",
)
async def update_learning_profile(
    payload: LearningProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await LearningService.update_profile(
        db,
        current_user.id,
        target_role=payload.target_role,
        target_level=payload.target_level,
        hours_per_week=payload.hours_per_week,
    )
    return profile


# -------------------------------------------------------------
# 2. Skill Performance Analysis
# -------------------------------------------------------------
@router.get(
    "/skills",
    response_model=list[SkillPerformanceItem],
    summary="Get calculated performance across all candidate skills",
)
async def get_skills_performance(
    force_sync: bool = Query(False, description="Recalculate skills from latest interviews & coding"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skills = await LearningService.get_user_skills(db, current_user.id, force_sync=force_sync)
    return [
        SkillPerformanceItem(
            id=s.id,
            canonical_skill=s.canonical_skill,
            category=s.category,
            interview_score=s.interview_score,
            interview_attempts=s.interview_attempts,
            coding_score=s.coding_score,
            coding_attempts=s.coding_attempts,
            combined_score=s.combined_score,
            total_attempts=s.total_attempts,
            status=s.status,
            confidence=s.confidence,
            last_assessed_at=s.last_assessed_at,
            reason=None,
        )
        for s in skills
    ]


# -------------------------------------------------------------
# 3. Weak Topic Detection
# -------------------------------------------------------------
@router.get(
    "/weak-topics",
    response_model=list[WeakTopicItem],
    summary="Detect and prioritize candidate's weak technical topics",
)
async def get_weak_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    topics = await LearningService.get_weak_topics(db, current_user.id)
    return [WeakTopicItem(**t) for t in topics]


# -------------------------------------------------------------
# 4. Learning Roadmap
# -------------------------------------------------------------
@router.get(
    "/roadmap",
    response_model=LearningRoadmapResponse,
    summary="Get active personalized multi-week learning roadmap",
)
async def get_learning_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = await LearningService.generate_or_get_roadmap(db, current_user.id)
    return roadmap


@router.post(
    "/roadmap/generate",
    response_model=LearningRoadmapResponse,
    summary="Generate or regenerate personalized roadmap",
)
async def generate_learning_roadmap(
    payload: RoadmapGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = await LearningService.generate_or_get_roadmap(
        db,
        current_user.id,
        target_role=payload.target_role,
        target_level=payload.target_level,
        force_regenerate=True,
    )

    try:
        from app.modules.notifications.service import NotificationService
        await NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            type="LEARNING_PLAN",
            title="Personalized Learning Plan Ready",
            message=f"Your personalized learning roadmap for {payload.target_role or 'your target role'} is ready!",
            commit=True,
        )
    except Exception as exc:
        pass

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        await publish_event(
            WebSocketEventType.LEARNING_PLAN_UPDATED.value,
            {
                "user_id": str(current_user.id),
                "target_role": payload.target_role,
                "target_level": payload.target_level,
            },
            user_id=current_user.id,
        )
    except Exception as ws_err:
        pass

    return roadmap


# -------------------------------------------------------------
# 5. Learning Resources
# -------------------------------------------------------------
@router.get(
    "/resources",
    response_model=list[LearningResourceItem],
    summary="Get recommended technical learning resources",
)
async def get_resources(
    topic: str | None = Query(None, description="Filter resources by topic"),
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resources = await LearningService.get_learning_resources(
        db,
        current_user.id,
        topic=topic,
        limit=limit,
    )
    return resources


# -------------------------------------------------------------
# 6. Consolidated Recommendations (Interview, Coding, Resources)
# -------------------------------------------------------------
@router.get(
    "/recommendations",
    response_model=ConsolidatedRecommendationsResponse,
    summary="Get unified recommendations across RAG questions, coding challenges & resources",
)
async def get_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    weak_raw = await LearningService.get_weak_topics(db, current_user.id)
    weak_items = [WeakTopicItem(**w) for w in weak_raw]

    resources_raw = await LearningService.get_learning_resources(db, current_user.id, limit=4)
    resources = [
        LearningResourceItem(
            id=r.id,
            title=r.title,
            description=r.description,
            topic=r.topic,
            canonical_skill=r.canonical_skill,
            difficulty=r.difficulty,
            resource_type=r.resource_type,
            url=r.url,
            estimated_duration_mins=r.estimated_duration_mins,
            source=r.source,
            quality_rating=r.quality_rating,
        )
        for r in resources_raw
    ]

    interview_practice = await LearningService.get_interview_recommendations(db, current_user.id, limit=4)
    coding_challenges = await LearningService.get_coding_recommendations(db, current_user.id, limit=4)

    return ConsolidatedRecommendationsResponse(
        weak_topics=weak_items,
        resources=resources,
        interview_practice=interview_practice,
        coding_challenges=coding_challenges,
        generated_at=datetime.now(timezone.utc),
    )


# -------------------------------------------------------------
# 7. Daily Practice Plan
# -------------------------------------------------------------
@router.get(
    "/daily-plan",
    response_model=DailyPracticePlanResponse,
    summary="Get today's tailored practice plan",
)
async def get_daily_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await LearningService.get_or_create_daily_plan(db, current_user.id)
    items = plan.items or []
    completed_count = sum(1 for it in items if it.get("is_completed"))
    pct = round((completed_count / len(items)) * 100.0, 1) if items else 0.0

    return DailyPracticePlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        plan_date=plan.plan_date,
        items=items,
        is_completed=plan.is_completed,
        completed_at=plan.completed_at,
        progress_percentage=pct,
    )


@router.post(
    "/daily-plan/{task_id}/toggle",
    response_model=DailyPracticePlanResponse,
    summary="Toggle completion status of a daily practice task",
)
async def toggle_daily_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await LearningService.complete_daily_task(db, current_user.id, task_id)
    items = plan.items or []
    completed_count = sum(1 for it in items if it.get("is_completed"))
    pct = round((completed_count / len(items)) * 100.0, 1) if items else 0.0

    return DailyPracticePlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        plan_date=plan.plan_date,
        items=items,
        is_completed=plan.is_completed,
        completed_at=plan.completed_at,
        progress_percentage=pct,
    )


# -------------------------------------------------------------
# 8. Weekly Goals
# -------------------------------------------------------------
@router.get(
    "/weekly-goals",
    response_model=list[WeeklyGoalItem],
    summary="Get current weekly practice goals and status",
)
async def get_weekly_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goals = await LearningService.get_or_create_weekly_goals(db, current_user.id)
    return [
        WeeklyGoalItem(
            id=g.id,
            user_id=g.user_id,
            week_start_date=g.week_start_date,
            title=g.title,
            goal_type=g.goal_type,
            target_count=g.target_count,
            completed_count=g.completed_count,
            deadline=g.deadline,
            status=g.status,
            progress_percentage=round((g.completed_count / g.target_count) * 100.0, 1) if g.target_count > 0 else 0.0,
        )
        for g in goals
    ]


@router.post(
    "/weekly-goals/{goal_id}/increment",
    response_model=WeeklyGoalItem,
    summary="Increment progress on a weekly goal",
)
async def increment_weekly_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = await LearningService.complete_weekly_goal_step(db, current_user.id, goal_id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly goal not found",
        )
    return WeeklyGoalItem(
        id=goal.id,
        user_id=goal.user_id,
        week_start_date=goal.week_start_date,
        title=goal.title,
        goal_type=goal.goal_type,
        target_count=goal.target_count,
        completed_count=goal.completed_count,
        deadline=goal.deadline,
        status=goal.status,
        progress_percentage=round((goal.completed_count / goal.target_count) * 100.0, 1) if goal.target_count > 0 else 0.0,
    )


# -------------------------------------------------------------
# 9. Learning Progress Tracking
# -------------------------------------------------------------
@router.get(
    "/progress",
    response_model=LearningProgressResponse,
    summary="Track overall learning progress, readiness & skill score deltas",
)
async def get_learning_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = await LearningService.get_learning_progress(db, current_user.id)
    return progress
