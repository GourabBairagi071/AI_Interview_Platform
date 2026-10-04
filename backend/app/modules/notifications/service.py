import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.model import Notification
from app.modules.notifications.schema import (
    CATEGORY_TO_TYPES,
    TYPE_TO_CATEGORY,
    NotificationItem,
    NotificationListResponse,
    NotificationType,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_notification_item(notif: Notification) -> NotificationItem:
    cat = TYPE_TO_CATEGORY.get(notif.type, "System")
    return NotificationItem(
        id=str(notif.id),
        type=notif.type,
        title=notif.title,
        message=notif.message,
        icon=notif.icon,
        category=cat,
        is_read=notif.is_read,
        created_at=notif.created_at.isoformat() if notif.created_at else utc_now().isoformat(),
        read_at=notif.read_at.isoformat() if notif.read_at else None,
        action_url=notif.action_url,
        priority=notif.priority,
        metadata=notif.metadata_json or {},
    )


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        type: str,
        title: str,
        message: str,
        icon: str = "🔔",
        event_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        action_url: str | None = None,
        priority: str = "normal",
        commit: bool = True,
    ) -> Notification | None:
        """
        Creates a notification for the user with duplicate protection via event_key.
        """
        if event_key:
            # Check if notification with this event_key already exists for this user
            stmt_check = select(Notification).where(
                Notification.user_id == user_id,
                Notification.event_key == event_key,
            )
            res_check = await db.execute(stmt_check)
            existing = res_check.scalar_one_or_none()
            if existing:
                return existing

        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            icon=icon,
            event_key=event_key,
            metadata_json=metadata or {},
            is_read=False,
            action_url=action_url,
            priority=priority,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        db.add(notif)
        if commit:
            try:
                await db.commit()
                await db.refresh(notif)
            except Exception as e:
                await db.rollback()
                logger.warning("Notification creation failed or duplicate detected: %s", e)
                # Re-query in case of race condition duplicate
                if event_key:
                    res_race = await db.execute(
                        select(Notification).where(
                            Notification.user_id == user_id,
                            Notification.event_key == event_key,
                        )
                    )
                    return res_race.scalar_one_or_none()
        if notif and notif.id:
            try:
                from app.core.websocket import publish_event, WebSocketEventType
                item = _to_notification_item(notif)
                await publish_event(
                    WebSocketEventType.NOTIFICATION_CREATED.value,
                    item.model_dump(),
                    user_id=user_id,
                )
            except Exception as ws_err:
                logger.warning("Failed to broadcast notification event: %s", ws_err)

        return notif

    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """
        Calculates user's unread count using database-level COUNT.
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        res = await db.execute(stmt)
        return int(res.scalar_one() or 0)

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
        category: str | None = None,
        type_filter: str | None = None,
    ) -> NotificationListResponse:
        """
        Returns paginated, sorted, filtered notifications for the authenticated user.
        """
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100

        # Base filter strictly by user_id
        base_conditions = [Notification.user_id == user_id]

        if unread_only:
            base_conditions.append(Notification.is_read.is_(False))

        if category:
            cat_lower = category.lower().strip()
            if cat_lower == "unread":
                base_conditions.append(Notification.is_read.is_(False))
            elif cat_lower in CATEGORY_TO_TYPES:
                allowed_types = CATEGORY_TO_TYPES[cat_lower]
                base_conditions.append(Notification.type.in_(allowed_types))

        if type_filter:
            base_conditions.append(Notification.type == type_filter)

        # Count total matching
        total_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(*base_conditions)
        )
        total_res = await db.execute(total_stmt)
        total = int(total_res.scalar_one() or 0)

        # Count overall unread for user
        unread_count = await NotificationService.get_unread_count(db, user_id)

        # Query paginated rows
        offset = (page - 1) * limit
        query_stmt = (
            select(Notification)
            .where(*base_conditions)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows_res = await db.execute(query_stmt)
        rows = list(rows_res.scalars().all())

        items = [_to_notification_item(r) for r in rows]
        has_next = (offset + len(items)) < total

        return NotificationListResponse(
            notifications=items,
            total=total,
            page=page,
            limit=limit,
            unread_count=unread_count,
            has_next=has_next,
        )

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> Notification | None:
        """
        Marks a specific notification as read, enforcing strict user ownership.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        res = await db.execute(stmt)
        notif = res.scalar_one_or_none()
        if not notif:
            return None

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = utc_now()
            notif.updated_at = utc_now()
            await db.commit()
            await db.refresh(notif)

            try:
                from app.core.websocket import publish_event, WebSocketEventType
                unread_cnt = await NotificationService.get_unread_count(db, user_id)
                await publish_event(
                    WebSocketEventType.NOTIFICATION_READ.value,
                    {"id": str(notif.id), "is_read": True, "unread_count": unread_cnt},
                    user_id=user_id,
                )
            except Exception as ws_err:
                logger.warning("Failed to broadcast notification read event: %s", ws_err)

        return notif

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """
        Atomically marks all unread notifications for the user as read.
        """
        now = utc_now()
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=now,
                updated_at=now,
            )
        )
        res = await db.execute(stmt)
        await db.commit()

        try:
            from app.core.websocket import publish_event, WebSocketEventType
            await publish_event(
                WebSocketEventType.NOTIFICATION_READ.value,
                {"all": True, "unread_count": 0},
                user_id=user_id,
            )
        except Exception as ws_err:
            logger.warning("Failed to broadcast notification all-read event: %s", ws_err)

        return res.rowcount or 0

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> bool:
        """
        Deletes a specific notification with strict user ownership.
        """
        stmt = delete(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        res = await db.execute(stmt)
        await db.commit()
        return (res.rowcount or 0) > 0

    @staticmethod
    async def sync_platform_events(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        """
        Ensures existing achievements, interview completion, practice milestones,
        and streaks that already exist in the database have corresponding real
        notifications generated idempotently.
        """
        # 1. Sync Unlocked Achievements
        from app.modules.achievements.model import UserAchievement, AchievementDefinition
        ach_stmt = (
            select(UserAchievement, AchievementDefinition)
            .join(AchievementDefinition, UserAchievement.achievement_id == AchievementDefinition.id)
            .where(UserAchievement.user_id == user_id, UserAchievement.unlocked.is_(True))
        )
        ach_res = await db.execute(ach_stmt)
        for user_ach, defn in ach_res.all():
            event_key = f"achievement_unlocked:{user_id}:{defn.id}"
            await NotificationService.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.ACHIEVEMENT_UNLOCKED.value,
                title=f"Achievement Unlocked: {defn.name}",
                message=f"You unlocked '{defn.name}'! {defn.description} (+{defn.xp_reward} XP)",
                icon=defn.icon or "🏆",
                event_key=event_key,
                metadata={
                    "achievement_id": defn.id,
                    "category": defn.category,
                    "xp_reward": defn.xp_reward,
                    "rarity": defn.rarity,
                },
                action_url="/achievements",
                priority="high",
                commit=False,
            )

        # 2. Sync Completed Interviews
        from app.modules.interview.model import Interview
        int_stmt = (
            select(Interview)
            .where(Interview.user_id == user_id, Interview.status == "completed")
            .order_by(Interview.created_at.desc())
        )
        int_res = await db.execute(int_stmt)
        for inter in int_res.scalars().all():
            event_key = f"interview_completed:{user_id}:{inter.id}"
            msg = f"Your mock interview for '{inter.job_role or 'Software Engineer'}' is completed."
            if inter.score is not None:
                msg += f" Final Score: {inter.score}%."
            await NotificationService.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.INTERVIEW_COMPLETED.value,
                title="Interview Completed",
                message=msg,
                icon="💼",
                event_key=event_key,
                metadata={
                    "interview_id": str(inter.id),
                    "job_role": inter.job_role,
                    "score": inter.score,
                },
                action_url=f"/interview/{inter.id}/results",
                priority="normal",
                commit=False,
            )

        # 3. Sync Level and Streak from Practice Progress
        from app.modules.practice.model import PracticeProgress
        from app.modules.practice.service import (
            load_all_platform_questions,
            _calculate_xp_from_records,
            _calculate_streak_from_records,
        )
        prog_stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
        prog_res = await db.execute(prog_stmt)
        records = list(prog_res.scalars().all())

        if records:
            catalog = await load_all_platform_questions(db)
            _, xp_stats = _calculate_xp_from_records(catalog, records)
            if xp_stats.level > 1:
                for lvl in range(2, xp_stats.level + 1):
                    event_key = f"level_up:{user_id}:{lvl}"
                    await NotificationService.create_notification(
                        db=db,
                        user_id=user_id,
                        type=NotificationType.LEVEL_UP.value,
                        title=f"Level Up! Level {lvl}",
                        message=f"You reached Level {lvl} rank on Question Practice!",
                        icon="⭐",
                        event_key=event_key,
                        metadata={"level": lvl, "total_xp": xp_stats.total_xp},
                        action_url="/practice",
                        priority="high",
                        commit=False,
                    )

            streak = _calculate_streak_from_records(records)
            if streak.current_streak >= 3:
                # Milestone streak notifications (3, 7, 14, 30 days)
                for milestone in [3, 7, 14, 30]:
                    if streak.current_streak >= milestone:
                        event_key = f"streak_milestone:{user_id}:{milestone}"
                        await NotificationService.create_notification(
                            db=db,
                            user_id=user_id,
                            type=NotificationType.STREAK.value,
                            title=f"{milestone}-Day Streak Active! 🔥",
                            message=f"Incredible dedication! You have maintained a {milestone}-day practice streak.",
                            icon="🔥",
                            event_key=event_key,
                            metadata={"streak_days": streak.current_streak, "milestone": milestone},
                            action_url="/practice",
                            priority="normal",
                            commit=False,
                        )

            # Solved count milestone (e.g., 5, 25, 50, 100 solved)
            solved_count = sum(1 for r in records if r.solved)
            for m in [5, 25, 50, 100, 250, 500]:
                if solved_count >= m:
                    event_key = f"practice_milestone:{user_id}:{m}"
                    await NotificationService.create_notification(
                        db=db,
                        user_id=user_id,
                        type=NotificationType.PRACTICE_MILESTONE.value,
                        title=f"Practice Milestone: {m} Questions Solved!",
                        message=f"You have successfully solved {m} technical practice questions.",
                        icon="🎯",
                        event_key=event_key,
                        metadata={"solved_count": solved_count, "milestone": m},
                        action_url="/practice",
                        priority="normal",
                        commit=False,
                    )

        await db.commit()
