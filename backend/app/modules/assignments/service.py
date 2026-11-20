import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.model import Company
from app.modules.admin.service import AdminService
from app.modules.assignments.model import CandidateAssignment, CandidateAssignmentProgress
from app.modules.assignments.schema import CreateAssignmentRequest, SubmitAssignmentRequest
from app.modules.auth.model import User, UserProfile
from app.modules.notifications.service import NotificationService
from app.modules.payments.model import UserSubscription, SubscriptionPlan
from app.modules.learning.model import SkillPerformance

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssignmentService:
    @staticmethod
    async def resolve_candidate_recipients(
        db: AsyncSession,
        target_type: str,
        target_filter: dict[str, Any],
    ) -> list[uuid.UUID]:
        """Resolve eligible candidate user IDs based on targeting criteria."""
        tt = (target_type or "INDIVIDUAL").upper()

        if tt in ["INDIVIDUAL", "SINGLE"]:
            cand_id_str = target_filter.get("candidate_id") or target_filter.get("user_id")
            if cand_id_str:
                try:
                    return [uuid.UUID(str(cand_id_str))]
                except (ValueError, TypeError):
                    return []
            cand_ids = target_filter.get("candidate_ids", [])
            if cand_ids:
                return [uuid.UUID(str(cid)) for cid in cand_ids]
            return []

        if tt in ["GROUP", "SEGMENT"]:
            cand_ids = target_filter.get("candidate_ids", [])
            return [uuid.UUID(str(cid)) for cid in cand_ids if cid]

        if tt == "ROLE":
            role_target = target_filter.get("role", "CANDIDATE")
            res = await db.execute(
                select(User.id).where(and_(User.role == role_target, User.is_active.is_(True)))
            )
            return list(res.scalars().all())

        if tt == "SKILL":
            cand_ids = target_filter.get("candidate_ids", [])
            skill_raw = (
                target_filter.get("skill")
                or target_filter.get("skill_name")
                or target_filter.get("target_skill")
                or ""
            )
            if not isinstance(skill_raw, str):
                skill_raw = str(skill_raw)
            clean_skill = skill_raw.strip()

            # 1. Explicit candidate_ids provided under skill filter
            if cand_ids:
                valid_uuids = []
                for cid in cand_ids:
                    try:
                        valid_uuids.append(uuid.UUID(str(cid)))
                    except (ValueError, TypeError):
                        pass
                if valid_uuids:
                    res = await db.execute(
                        select(User.id).where(
                            and_(
                                User.id.in_(valid_uuids),
                                User.role == "CANDIDATE",
                                User.is_active.is_(True),
                            )
                        )
                    )
                    return list(res.scalars().all())

            # 2. Return empty list if skill target is empty or missing (never fall through to ALL!)
            if not clean_skill:
                return []

            # Escape regex special characters safely
            safe_regex = rf"\y{re.escape(clean_skill)}\y"

            # Query candidate profiles & evaluated skill performances safely
            res = await db.execute(
                select(User.id)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .where(
                    and_(
                        User.role == "CANDIDATE",
                        User.is_active.is_(True),
                        or_(
                            UserProfile.skills.op("~*")(safe_regex),
                            User.id.in_(
                                select(SkillPerformance.user_id).where(
                                    SkillPerformance.canonical_skill.ilike(f"%{clean_skill}%")
                                )
                            ),
                        ),
                    )
                )
            )
            return list(res.scalars().all())

        if tt == "SUBSCRIPTION_TIER":
            cand_ids = target_filter.get("candidate_ids", [])
            tier_raw = (
                target_filter.get("plan_code")
                or target_filter.get("tier")
                or target_filter.get("plan_name")
                or ""
            )
            if not isinstance(tier_raw, str):
                tier_raw = str(tier_raw)
            tier_code = tier_raw.strip().upper()

            # 1. Explicit candidate_ids provided under subscription filter
            if cand_ids:
                valid_uuids = []
                for cid in cand_ids:
                    try:
                        valid_uuids.append(uuid.UUID(str(cid)))
                    except (ValueError, TypeError):
                        pass
                if valid_uuids:
                    res = await db.execute(
                        select(User.id).where(
                            and_(
                                User.id.in_(valid_uuids),
                                User.role == "CANDIDATE",
                                User.is_active.is_(True),
                            )
                        )
                    )
                    return list(res.scalars().all())

            # 2. Return empty list if tier target is empty or missing (never fall through to ALL!)
            if not tier_code:
                return []

            now = utc_now()

            # Subquery selecting active paid subscription user IDs (PRO / PREMIUM / paid)
            active_paid_sub = (
                select(UserSubscription.user_id)
                .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
                .where(
                    and_(
                        UserSubscription.status == "active",
                        or_(UserSubscription.expires_at.is_(None), UserSubscription.expires_at > now),
                        or_(
                            SubscriptionPlan.price > 0,
                            SubscriptionPlan.name.ilike("%PRO%"),
                            SubscriptionPlan.name.ilike("%PREMIUM%"),
                            SubscriptionPlan.slug.ilike("%PRO%"),
                            SubscriptionPlan.slug.ilike("%PREMIUM%"),
                        ),
                    )
                )
            )

            if tier_code in ["FREE", "DEFAULT"]:
                # Candidates without active paid subscription are treated as FREE tier
                res = await db.execute(
                    select(User.id).where(
                        and_(
                            User.role == "CANDIDATE",
                            User.is_active.is_(True),
                            User.id.not_in(active_paid_sub),
                        )
                    )
                )
                return list(res.scalars().all())

            # For PRO, PREMIUM, or other paid tiers, query active matching subscription holders
            res = await db.execute(
                select(User.id)
                .join(UserSubscription, UserSubscription.user_id == User.id)
                .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
                .where(
                    and_(
                        User.role == "CANDIDATE",
                        User.is_active.is_(True),
                        UserSubscription.status == "active",
                        or_(UserSubscription.expires_at.is_(None), UserSubscription.expires_at > now),
                        or_(
                            SubscriptionPlan.name.ilike(f"%{tier_code}%"),
                            SubscriptionPlan.slug.ilike(f"%{tier_code}%"),
                        ),
                    )
                )
            )
            return list(res.scalars().all())

        if tt == "COMPANY":
            cand_ids = target_filter.get("candidate_ids", [])
            company_target = (
                target_filter.get("company_id")
                or target_filter.get("company_name")
                or target_filter.get("company")
                or ""
            )
            if not isinstance(company_target, str):
                company_target = str(company_target)
            company_target = company_target.strip()

            # 1. Explicit candidate IDs passed under company filter
            if cand_ids:
                valid_uuids = []
                for cid in cand_ids:
                    try:
                        valid_uuids.append(uuid.UUID(str(cid)))
                    except (ValueError, TypeError):
                        pass
                if valid_uuids:
                    res = await db.execute(
                        select(User.id).where(
                            and_(
                                User.id.in_(valid_uuids),
                                User.role == "CANDIDATE",
                                User.is_active.is_(True),
                            )
                        )
                    )
                    return list(res.scalars().all())

            # 2. Return empty list if no company target specified (never fall through to ALL!)
            if not company_target:
                return []

            # 3. Lookup Company object by ID or name
            company_obj = None
            try:
                comp_uuid = uuid.UUID(company_target)
                comp_res = await db.execute(select(Company).where(Company.id == comp_uuid))
                company_obj = comp_res.scalar_one_or_none()
            except (ValueError, TypeError):
                comp_res = await db.execute(
                    select(Company).where(
                        and_(Company.is_active.is_(True), Company.name.ilike(f"%{company_target}%"))
                    )
                )
                company_obj = comp_res.scalars().first()

            search_name = company_obj.name if company_obj else company_target

            # 4. Search candidates matching company name in user profile or email domain
            res = await db.execute(
                select(User.id)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .where(
                    and_(
                        User.role == "CANDIDATE",
                        User.is_active.is_(True),
                        or_(
                            UserProfile.headline.ilike(f"%{search_name}%"),
                            UserProfile.bio.ilike(f"%{search_name}%"),
                            UserProfile.education.ilike(f"%{search_name}%"),
                            UserProfile.target_role.ilike(f"%{search_name}%"),
                            User.email.ilike(f"%@{search_name.lower().replace(' ', '')}.com"),
                        ),
                    )
                )
            )
            return list(res.scalars().all())

        # Default / ALL: All active candidates
        res = await db.execute(
            select(User.id).where(and_(User.role == "CANDIDATE", User.is_active.is_(True)))
        )
        return list(res.scalars().all())

    @staticmethod
    async def create_assignment(
        db: AsyncSession,
        data: CreateAssignmentRequest,
        actor: User,
    ) -> CandidateAssignment:
        """Create an assignment and dispatch to resolved candidate recipients."""
        assignment = CandidateAssignment(
            title=data.title.strip(),
            description=data.description,
            assignment_type=data.assignment_type.upper(),
            content_id=str(data.content_id) if data.content_id else None,
            content_payload=data.content_payload or {},
            instructions=data.instructions,
            priority=data.priority.upper(),
            target_type=data.target_type.upper(),
            target_filter=data.target_filter or {},
            scheduled_for=data.scheduled_for,
            start_date=data.start_date or utc_now(),
            due_date=data.due_date,
            time_limit_mins=data.time_limit_mins,
            attempt_limit=max(1, data.attempt_limit),
            created_by_admin_id=actor.id,
            status="SCHEDULED" if data.scheduled_for and data.scheduled_for > utc_now() else "ASSIGNED",
            metadata_json=data.metadata_json or {},
        )
        db.add(assignment)
        await db.flush()

        # Resolve candidate recipients
        recipient_ids = await AssignmentService.resolve_candidate_recipients(
            db=db,
            target_type=data.target_type,
            target_filter=data.target_filter,
        )

        # Create progress records atomically
        for cid in recipient_ids:
            progress = CandidateAssignmentProgress(
                assignment_id=assignment.id,
                candidate_id=cid,
                status="ASSIGNED",
                progress_percent=0.0,
                attempt_count=0,
            )
            db.add(progress)

        await db.commit()
        await db.refresh(assignment)

        # Notify candidates if published immediately
        if assignment.status == "ASSIGNED":
            for cid in recipient_ids:
                try:
                    await NotificationService.create_notification(
                        db=db,
                        user_id=cid,
                        type="system",
                        title=f"New Task Assigned: {assignment.title}",
                        message=f"You have been assigned a {assignment.assignment_type} task. Priority: {assignment.priority}.",
                        icon="📋",
                        action_url="/dashboard",
                    )
                except Exception:
                    pass

        # Audit log
        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="ASSIGNMENT_CREATE",
            resource="candidate_assignment",
            resource_id=str(assignment.id),
            details={
                "title": assignment.title,
                "type": assignment.assignment_type,
                "recipients_count": len(recipient_ids),
                "target_type": assignment.target_type,
            },
        )

        return assignment

    @staticmethod
    async def list_admin_assignments(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        assignment_type: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List assignments with calculated completion metrics."""
        query = select(CandidateAssignment)

        if status:
            query = query.where(CandidateAssignment.status == status.upper())
        if assignment_type:
            query = query.where(CandidateAssignment.assignment_type == assignment_type.upper())
        if search:
            query = query.where(CandidateAssignment.title.ilike(f"%{search.strip()}%"))

        subq = query.subquery()
        count_query = select(func.count()).select_from(subq)
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(desc(CandidateAssignment.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        assignments = (await db.execute(query)).scalars().all()

        items = []
        for a in assignments:
            # Aggregate stats from progress records
            stats_query = select(
                func.count(CandidateAssignmentProgress.id).label("total"),
                func.count(CandidateAssignmentProgress.id).filter(
                    CandidateAssignmentProgress.status == "IN_PROGRESS"
                ).label("started"),
                func.count(CandidateAssignmentProgress.id).filter(
                    CandidateAssignmentProgress.status == "COMPLETED"
                ).label("completed"),
                func.count(CandidateAssignmentProgress.id).filter(
                    CandidateAssignmentProgress.status == "ASSIGNED"
                ).label("pending"),
                func.count(CandidateAssignmentProgress.id).filter(
                    CandidateAssignmentProgress.status == "EXPIRED"
                ).label("expired"),
                func.avg(CandidateAssignmentProgress.score).filter(
                    CandidateAssignmentProgress.status == "COMPLETED"
                ).label("avg_score"),
            ).where(CandidateAssignmentProgress.assignment_id == a.id)

            stat_res = (await db.execute(stats_query)).one()
            t_total = stat_res.total or 0
            t_completed = stat_res.completed or 0
            rate = round((t_completed / t_total * 100), 1) if t_total > 0 else 0.0

            items.append({
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "assignment_type": a.assignment_type,
                "content_id": a.content_id,
                "priority": a.priority,
                "target_type": a.target_type,
                "status": a.status,
                "scheduled_for": a.scheduled_for,
                "due_date": a.due_date,
                "attempt_limit": a.attempt_limit,
                "created_at": a.created_at,
                "total_assigned": t_total,
                "total_started": stat_res.started or 0,
                "total_completed": t_completed,
                "total_pending": stat_res.pending or 0,
                "total_expired": stat_res.expired or 0,
                "completion_rate": rate,
                "avg_score": round(stat_res.avg_score, 1) if stat_res.avg_score is not None else None,
            })

        return {"assignments": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def get_admin_assignment_detail(
        db: AsyncSession,
        assignment_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Get complete assignment detail with candidate-level progress."""
        res = await db.execute(
            select(CandidateAssignment).where(CandidateAssignment.id == assignment_id)
        )
        a = res.scalar_one_or_none()
        if not a:
            return None

        # Fetch progress joined with user details
        prog_query = (
            select(CandidateAssignmentProgress, User.full_name, User.email)
            .join(User, CandidateAssignmentProgress.candidate_id == User.id)
            .where(CandidateAssignmentProgress.assignment_id == assignment_id)
            .order_by(desc(CandidateAssignmentProgress.updated_at))
        )
        prog_rows = (await db.execute(prog_query)).all()

        recipients = []
        c_completed = 0
        c_started = 0
        c_pending = 0
        c_expired = 0
        scores = []

        for p, full_name, email in prog_rows:
            if p.status == "COMPLETED":
                c_completed += 1
                if p.score is not None:
                    scores.append(p.score)
            elif p.status == "IN_PROGRESS":
                c_started += 1
            elif p.status == "EXPIRED":
                c_expired += 1
            else:
                c_pending += 1

            recipients.append({
                "id": str(p.id),
                "candidate_id": str(p.candidate_id),
                "candidate_name": full_name or email,
                "candidate_email": email,
                "status": p.status,
                "progress_percent": p.progress_percent,
                "score": p.score,
                "attempt_count": p.attempt_count,
                "started_at": p.started_at,
                "completed_at": p.completed_at,
                "submission_ref_id": p.submission_ref_id,
                "created_at": p.created_at,
            })

        total = len(recipients)
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        rate = round((c_completed / total * 100), 1) if total > 0 else 0.0

        return {
            "id": str(a.id),
            "title": a.title,
            "description": a.description,
            "assignment_type": a.assignment_type,
            "content_id": a.content_id,
            "content_payload": a.content_payload,
            "instructions": a.instructions,
            "priority": a.priority,
            "target_type": a.target_type,
            "target_filter": a.target_filter,
            "status": a.status,
            "scheduled_for": a.scheduled_for,
            "due_date": a.due_date,
            "time_limit_mins": a.time_limit_mins,
            "attempt_limit": a.attempt_limit,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "total_assigned": total,
            "total_started": c_started,
            "total_completed": c_completed,
            "total_pending": c_pending,
            "total_expired": c_expired,
            "completion_rate": rate,
            "avg_score": avg_score,
            "recipients": recipients,
        }

    @staticmethod
    async def update_assignment_status(
        db: AsyncSession,
        assignment_id: uuid.UUID,
        new_status: str,
        actor: User,
    ) -> bool:
        """Update assignment status (CANCEL, ARCHIVE, PUBLISH)."""
        res = await db.execute(
            select(CandidateAssignment).where(CandidateAssignment.id == assignment_id)
        )
        a = res.scalar_one_or_none()
        if not a:
            return False

        a.status = new_status.upper()
        a.updated_at = utc_now()
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="ASSIGNMENT_STATUS_UPDATE",
            resource="candidate_assignment",
            resource_id=str(a.id),
            details={"new_status": a.status},
        )
        return True

    # ============================================================
    # CANDIDATE ACTIONS & INBOX (Zero IDOR)
    # ============================================================
    @staticmethod
    async def get_candidate_assigned_tasks(
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch assigned tasks strictly for the authenticated candidate."""
        now = utc_now()

        # Query assigned tasks
        query = (
            select(CandidateAssignmentProgress, CandidateAssignment)
            .join(CandidateAssignment, CandidateAssignmentProgress.assignment_id == CandidateAssignment.id)
            .where(
                and_(
                    CandidateAssignmentProgress.candidate_id == candidate_id,
                    CandidateAssignment.status.in_(["ASSIGNED", "IN_PROGRESS", "COMPLETED"]),
                )
            )
            .order_by(desc(CandidateAssignment.priority), desc(CandidateAssignment.created_at))
        )
        rows = (await db.execute(query)).all()

        results = []
        for p, a in rows:
            # Check server-authoritative expiration
            effective_status = p.status
            if a.due_date and a.due_date < now and effective_status not in ["COMPLETED", "SUBMITTED"]:
                if effective_status != "EXPIRED":
                    p.status = "EXPIRED"
                    p.expired_at = now
                    await db.commit()
                effective_status = "EXPIRED"

            results.append({
                "id": str(p.id),
                "assignment_id": str(a.id),
                "title": a.title,
                "description": a.description,
                "assignment_type": a.assignment_type,
                "content_id": a.content_id,
                "content_payload": a.content_payload,
                "instructions": a.instructions,
                "priority": a.priority,
                "status": effective_status,
                "progress_percent": p.progress_percent,
                "score": p.score,
                "attempt_count": p.attempt_count,
                "attempt_limit": a.attempt_limit,
                "due_date": a.due_date,
                "time_limit_mins": a.time_limit_mins,
                "started_at": p.started_at,
                "completed_at": p.completed_at,
                "created_at": a.created_at,
            })

        return results

    @staticmethod
    async def start_candidate_assignment(
        db: AsyncSession,
        assignment_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Start or continue assigned task (strictly verifies candidate ownership)."""
        res = await db.execute(
            select(CandidateAssignmentProgress, CandidateAssignment)
            .join(CandidateAssignment, CandidateAssignmentProgress.assignment_id == CandidateAssignment.id)
            .where(
                and_(
                    CandidateAssignmentProgress.assignment_id == assignment_id,
                    CandidateAssignmentProgress.candidate_id == candidate_id,
                )
            )
            .with_for_update(of=CandidateAssignmentProgress)
        )
        row = res.one_or_none()
        if not row:
            return None

        p, a = row
        now = utc_now()

        # Check due date
        if a.due_date and a.due_date < now and p.status != "COMPLETED":
            p.status = "EXPIRED"
            await db.commit()
            return {"error": "Assignment has expired", "status": "EXPIRED"}

        # Check attempt limits
        if p.attempt_count >= a.attempt_limit and p.status == "COMPLETED":
            return {"error": "Attempt limit reached", "status": "COMPLETED"}

        p.status = "IN_PROGRESS"
        p.attempt_count += 1
        if not p.started_at:
            p.started_at = now
        p.updated_at = now

        await db.commit()
        await db.refresh(p)

        return {
            "id": str(p.id),
            "assignment_id": str(a.id),
            "assignment_type": a.assignment_type,
            "content_id": a.content_id,
            "content_payload": a.content_payload,
            "status": p.status,
            "attempt_count": p.attempt_count,
            "started_at": p.started_at,
        }

    @staticmethod
    async def submit_candidate_assignment(
        db: AsyncSession,
        assignment_id: uuid.UUID,
        candidate_id: uuid.UUID,
        data: SubmitAssignmentRequest,
    ) -> dict[str, Any] | None:
        """Submit completed task and update candidate learning intelligence."""
        res = await db.execute(
            select(CandidateAssignmentProgress, CandidateAssignment)
            .join(CandidateAssignment, CandidateAssignmentProgress.assignment_id == CandidateAssignment.id)
            .where(
                and_(
                    CandidateAssignmentProgress.assignment_id == assignment_id,
                    CandidateAssignmentProgress.candidate_id == candidate_id,
                )
            )
            .with_for_update(of=CandidateAssignmentProgress)
        )
        row = res.one_or_none()
        if not row:
            return None

        p, a = row
        now = utc_now()

        # If already completed, return existing completed state cleanly (prevents duplicate submission race conditions)
        if p.status == "COMPLETED":
            return {
                "id": str(p.id),
                "status": p.status,
                "score": p.score,
                "completed_at": p.completed_at,
                "progress_percent": p.progress_percent,
            }

        p.status = "COMPLETED"
        p.progress_percent = 100.0
        p.score = data.score if data.score is not None else 100.0
        p.completed_at = now
        p.submission_ref_id = str(data.submission_ref_id) if data.submission_ref_id else None
        p.submission_data = data.submission_data or {}
        p.updated_at = now

        await db.commit()
        await db.refresh(p)

        # Notify candidate of completion
        try:
            await NotificationService.create_notification(
                db=db,
                user_id=candidate_id,
                type="achievement",
                title=f"Task Completed: {a.title}",
                message=f"Great job! Your assignment has been marked completed with score {p.score}%.",
                icon="🏆",
                action_url="/dashboard",
            )
        except Exception:
            pass

        # Trigger Learning Intelligence sync
        try:
            from app.modules.learning.evaluator import sync_and_persist_skill_performances
            await sync_and_persist_skill_performances(db, candidate_id)
        except Exception as e:
            logger.warning(f"Failed to sync learning intelligence for candidate {candidate_id}: {e}")

        return {
            "id": str(p.id),
            "status": p.status,
            "score": p.score,
            "completed_at": p.completed_at,
            "progress_percent": p.progress_percent,
        }

    @staticmethod
    async def get_assignment_analytics(db: AsyncSession) -> dict[str, Any]:
        """Aggregate global assignment metrics for admin dashboard."""
        total_assignments = (await db.execute(select(func.count(CandidateAssignment.id)))).scalar() or 0
        active_assignments = (
            await db.execute(
                select(func.count(CandidateAssignment.id)).where(CandidateAssignment.status == "ASSIGNED")
            )
        ).scalar() or 0
        completed_assignments = (
            await db.execute(
                select(func.count(CandidateAssignment.id)).where(CandidateAssignment.status == "COMPLETED")
            )
        ).scalar() or 0

        total_dispatches = (await db.execute(select(func.count(CandidateAssignmentProgress.id)))).scalar() or 0
        completed_dispatches = (
            await db.execute(
                select(func.count(CandidateAssignmentProgress.id)).where(
                    CandidateAssignmentProgress.status == "COMPLETED"
                )
            )
        ).scalar() or 0

        rate = round((completed_dispatches / total_dispatches * 100), 1) if total_dispatches > 0 else 0.0
        avg_score = (
            await db.execute(
                select(func.avg(CandidateAssignmentProgress.score)).where(
                    CandidateAssignmentProgress.status == "COMPLETED"
                )
            )
        ).scalar()

        # Breakdown by type
        type_res = await db.execute(
            select(CandidateAssignment.assignment_type, func.count(CandidateAssignment.id)).group_by(
                CandidateAssignment.assignment_type
            )
        )
        by_type = {t: c for t, c in type_res.all()}

        # Breakdown by priority
        prio_res = await db.execute(
            select(CandidateAssignment.priority, func.count(CandidateAssignment.id)).group_by(
                CandidateAssignment.priority
            )
        )
        by_priority = {p: c for p, c in prio_res.all()}

        return {
            "total_assignments": total_assignments,
            "active_assignments": active_assignments,
            "completed_assignments": completed_assignments,
            "total_task_dispatches": total_dispatches,
            "overall_completion_rate": rate,
            "avg_assignment_score": round(avg_score, 1) if avg_score is not None else None,
            "by_type": by_type,
            "by_priority": by_priority,
        }
