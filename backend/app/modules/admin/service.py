import json
import logging
from pathlib import Path
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, cast, Date, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.websocket.events import WebSocketEventType
from app.core.websocket.publisher import publish_event
from app.modules.achievements.model import AchievementDefinition, UserAchievement
from app.modules.admin.model import (
    AdminAuditLog,
    AdminRole,
    AIAgentConfig,
    Company,
    SystemSetting,
)
from app.modules.admin.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from app.modules.admin.schema import (
    BroadcastNotificationRequest,
    CreateAchievementRequest,
    CreateCompanyRequest,
    CreateCouponRequest,
    CreateQuestionRequest,
    CreateResourceRequest,
    CreateSubscriptionPlanRequest,
    UpdateAIAgentConfigRequest,
    UpdateCompanyRequest,
    UpdateQuestionRequest,
    UpdateResourceRequest,
)
from app.modules.auth.model import User, UserProfile
from app.modules.coding.contest_model import (
    Contest,
    ContestParticipantStats,
    ContestProblem,
    ContestRegistration,
    ContestSubmission,
)
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.interview.model import Interview
from app.modules.learning.model import (
    LearningProfile,
    LearningResource,
    LearningRoadmap,
    SkillPerformance,
)
from app.modules.notifications.model import Notification
from app.modules.payments.model import (
    Coupon,
    Invoice,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
)
from app.modules.practice.model import PracticeProgress, PracticeQuestion
from app.modules.rag.model import InterviewQuestionVector
from app.modules.resume.model import Resume
from app.modules.support.model import Feedback, SupportTicket, SupportTicketMessage

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AdminService:
    # ============================================================
    # 1. AUDIT LOGGING HELPER
    # ============================================================
    @staticmethod
    async def log_audit(
        db: AsyncSession,
        actor: User,
        action: str,
        resource: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AdminAuditLog:
        """Create an immutable audit log entry for sensitive admin actions."""
        log_entry = AdminAuditLog(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else "system@interviewplatform.ai",
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return log_entry

    # ============================================================
    # 2. DASHBOARD OVERVIEW & KPIS (REAL POSTGRESQL DATA)
    # ============================================================
    @staticmethod
    async def get_dashboard_kpis(
        db: AsyncSession,
        time_range: str = "30d",
    ) -> dict[str, Any]:
        """Aggregate real-time metrics, growth charts, and recent activity from PostgreSQL."""
        now = utc_now()

        # 1. Parse time range and define temporal window
        if time_range == "today":
            since_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            days = 1
        elif time_range == "7d":
            since_date = now - timedelta(days=7)
            days = 7
        elif time_range == "30d":
            since_date = now - timedelta(days=30)
            days = 30
        elif time_range == "90d":
            since_date = now - timedelta(days=90)
            days = 90
        elif time_range in ("this_year", "year"):
            since_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            days = (now.date() - since_date.date()).days + 1
        else:  # "all"
            since_date = now - timedelta(days=3650)
            days = 365

        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # ----------------------------------------------------
        # USER KPIs (PostgreSQL table: users)
        # ----------------------------------------------------
        total_users_res = await db.execute(select(func.count(User.id)))
        total_users = total_users_res.scalar() or 0

        active_users_res = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_res.scalar() or 0

        new_users_res = await db.execute(
            select(func.count(User.id)).where(User.created_at >= since_date)
        )
        new_users_in_range = new_users_res.scalar() or 0

        new_users_7d_res = await db.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        )
        new_users_7d = new_users_7d_res.scalar() or 0

        new_users_30d_res = await db.execute(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        )
        new_users_30d = new_users_30d_res.scalar() or 0

        # ----------------------------------------------------
        # INTERVIEW KPIs (PostgreSQL table: interviews)
        # ----------------------------------------------------
        total_interviews_res = await db.execute(select(func.count(Interview.id)))
        total_interviews = total_interviews_res.scalar() or 0

        completed_interviews_res = await db.execute(
            select(func.count(Interview.id)).where(Interview.status == "completed")
        )
        completed_interviews = completed_interviews_res.scalar() or 0

        avg_score_res = await db.execute(
            select(func.avg(Interview.score)).where(
                and_(Interview.status == "completed", Interview.score.isnot(None))
            )
        )
        raw_avg_score = avg_score_res.scalar()
        avg_interview_score = round(float(raw_avg_score), 2) if raw_avg_score is not None else None

        # ----------------------------------------------------
        # ATS RESUME SCORING (Persisted resume analyses / Learning profiles)
        # ----------------------------------------------------
        resume_res = await db.execute(select(Resume))
        resumes = resume_res.scalars().all()
        ats_scores: list[float] = []
        for r in resumes:
            if not r.file_url:
                continue
            clean_url = r.file_url.lstrip("/").replace("\\", "/")
            for base in [Path("."), Path(".."), Path("backend")]:
                cand = base / clean_url
                analysis_path = cand.with_suffix(".analysis.json")
                if analysis_path.exists():
                    try:
                        data = json.loads(analysis_path.read_text(encoding="utf-8"))
                        s = data.get("ats_score") if data.get("ats_score") is not None else data.get("estimated_ats_score")
                        if s is not None:
                            ats_scores.append(float(s))
                    except Exception:
                        pass
                    break

        avg_readiness_res = await db.execute(
            select(func.avg(LearningProfile.overall_readiness_score)).where(
                LearningProfile.overall_readiness_score.isnot(None)
            )
        )
        raw_learning_ats = avg_readiness_res.scalar()

        if ats_scores:
            avg_ats_score = round(sum(ats_scores) / len(ats_scores), 2)
        elif raw_learning_ats is not None:
            avg_ats_score = round(float(raw_learning_ats), 2)
        else:
            avg_ats_score = None

        # ----------------------------------------------------
        # SUBSCRIPTION KPIs (PostgreSQL tables: user_subscriptions, subscription_plans)
        # ----------------------------------------------------
        total_plans_res = await db.execute(select(func.count(SubscriptionPlan.id)))
        total_subscription_plans = total_plans_res.scalar() or 0

        active_subs_res = await db.execute(
            select(func.count(UserSubscription.id)).where(
                and_(
                    UserSubscription.status == "active",
                    or_(UserSubscription.expires_at == None, UserSubscription.expires_at > now),
                )
            )
        )
        active_subscriptions = active_subs_res.scalar() or 0

        expired_subs_res = await db.execute(
            select(func.count(UserSubscription.id)).where(
                or_(
                    UserSubscription.status == "expired",
                    and_(
                        UserSubscription.status == "active",
                        UserSubscription.expires_at.isnot(None),
                        UserSubscription.expires_at <= now,
                    ),
                )
            )
        )
        expired_subscriptions = expired_subs_res.scalar() or 0

        cancelled_subs_res = await db.execute(
            select(func.count(UserSubscription.id)).where(UserSubscription.status == "cancelled")
        )
        cancelled_subscriptions = cancelled_subs_res.scalar() or 0

        pending_subs_res = await db.execute(
            select(func.count(UserSubscription.id)).where(UserSubscription.status == "pending")
        )
        pending_subscriptions = pending_subs_res.scalar() or 0

        # ----------------------------------------------------
        # PAYMENT KPIs (PostgreSQL table: payment_transactions)
        # ----------------------------------------------------
        total_tx_res = await db.execute(select(func.count(PaymentTransaction.id)))
        total_payment_transactions = total_tx_res.scalar() or 0

        paid_tx_res = await db.execute(
            select(func.count(PaymentTransaction.id)).where(PaymentTransaction.status == "paid")
        )
        successful_payments = paid_tx_res.scalar() or 0

        failed_tx_res = await db.execute(
            select(func.count(PaymentTransaction.id)).where(PaymentTransaction.status == "failed")
        )
        failed_payments = failed_tx_res.scalar() or 0

        pending_tx_res = await db.execute(
            select(func.count(PaymentTransaction.id)).where(
                PaymentTransaction.status.in_(["created", "pending"])
            )
        )
        pending_payments = pending_tx_res.scalar() or 0

        rev_res = await db.execute(
            select(func.sum(PaymentTransaction.amount)).where(
                PaymentTransaction.status == "paid"
            )
        )
        raw_rev = rev_res.scalar()
        total_revenue_inr = round(float(raw_rev) / 100.0, 2) if raw_rev else 0.0

        # ----------------------------------------------------
        # SUPPORT KPIs (PostgreSQL table: support_tickets)
        # ----------------------------------------------------
        total_tickets_res = await db.execute(select(func.count(SupportTicket.id)))
        total_support_tickets = total_tickets_res.scalar() or 0

        open_tickets_res = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
        )
        open_support_tickets = open_tickets_res.scalar() or 0

        in_prog_tickets_res = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == "in_progress")
        )
        in_progress_support_tickets = in_prog_tickets_res.scalar() or 0

        resolved_tickets_res = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == "resolved")
        )
        resolved_support_tickets = resolved_tickets_res.scalar() or 0

        closed_tickets_res = await db.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status == "closed")
        )
        closed_support_tickets = closed_tickets_res.scalar() or 0

        pending_tickets_res = await db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(["open", "in_progress", "waiting_user", "waiting_for_user"])
            )
        )
        pending_support_tickets = pending_tickets_res.scalar() or 0

        # ----------------------------------------------------
        # PRACTICE QUESTIONS, CODING, CONTESTS, RAG
        # ----------------------------------------------------
        tech_q_res = await db.execute(select(func.count(PracticeQuestion.id)))
        technical_questions = tech_q_res.scalar() or 0

        coding_prob_res = await db.execute(select(func.count(CodingProblem.id)))
        coding_problems = coding_prob_res.scalar() or 0

        coding_sub_res = await db.execute(select(func.count(CodingSubmission.id)))
        total_coding_submissions = coding_sub_res.scalar() or 0

        contest_res = await db.execute(select(func.count(Contest.id)))
        contests = contest_res.scalar() or 0

        contest_reg_res = await db.execute(select(func.count(ContestRegistration.id)))
        contest_participants = contest_reg_res.scalar() or 0

        rag_res = await db.execute(select(func.count(InterviewQuestionVector.id)))
        rag_question_count = rag_res.scalar() or 0

        # ----------------------------------------------------
        # TIME-SERIES CHARTS (PostgreSQL CAST(... AS DATE) aggregation)
        # ----------------------------------------------------
        timeline_start = max(since_date.date(), now.date() - timedelta(days=min(days, 90)))
        timeline_days: list[datetime.date] = []
        cur_day = timeline_start
        while cur_day <= now.date():
            timeline_days.append(cur_day)
            cur_day += timedelta(days=1)

        # 1. User registrations daily
        u_chart_stmt = (
            select(
                cast(User.created_at, Date).label("day"),
                func.count(User.id).label("cnt"),
            )
            .where(User.created_at >= since_date)
            .group_by(cast(User.created_at, Date))
            .order_by(cast(User.created_at, Date))
        )
        u_chart_map = {row.day: row.cnt for row in (await db.execute(u_chart_stmt)).all()}

        # 2. Interviews daily
        int_chart_stmt = (
            select(
                cast(Interview.created_at, Date).label("day"),
                func.count(Interview.id).label("cnt"),
            )
            .where(Interview.created_at >= since_date)
            .group_by(cast(Interview.created_at, Date))
            .order_by(cast(Interview.created_at, Date))
        )
        int_chart_map = {row.day: row.cnt for row in (await db.execute(int_chart_stmt)).all()}

        # 3. Completed interviews daily
        comp_int_stmt = (
            select(
                cast(Interview.created_at, Date).label("day"),
                func.count(Interview.id).label("cnt"),
            )
            .where(and_(Interview.created_at >= since_date, Interview.status == "completed"))
            .group_by(cast(Interview.created_at, Date))
            .order_by(cast(Interview.created_at, Date))
        )
        comp_int_map = {row.day: row.cnt for row in (await db.execute(comp_int_stmt)).all()}

        # 4. Revenue daily
        rev_chart_stmt = (
            select(
                cast(PaymentTransaction.created_at, Date).label("day"),
                func.sum(PaymentTransaction.amount).label("amt"),
            )
            .where(
                and_(
                    PaymentTransaction.status == "paid",
                    PaymentTransaction.created_at >= since_date,
                )
            )
            .group_by(cast(PaymentTransaction.created_at, Date))
            .order_by(cast(PaymentTransaction.created_at, Date))
        )
        rev_chart_map = {row.day: row.amt for row in (await db.execute(rev_chart_stmt)).all()}

        # 5. Support tickets daily
        supp_chart_stmt = (
            select(
                cast(SupportTicket.created_at, Date).label("day"),
                func.count(SupportTicket.id).label("cnt"),
            )
            .where(SupportTicket.created_at >= since_date)
            .group_by(cast(SupportTicket.created_at, Date))
            .order_by(cast(SupportTicket.created_at, Date))
        )
        supp_chart_map = {row.day: row.cnt for row in (await db.execute(supp_chart_stmt)).all()}

        user_growth_chart = [
            {
                "date": d.isoformat(),
                "count": u_chart_map.get(d, 0),
                "value": u_chart_map.get(d, 0),
            }
            for d in timeline_days
        ]

        interview_activity_chart = [
            {
                "date": d.isoformat(),
                "count": int_chart_map.get(d, 0),
                "value": int_chart_map.get(d, 0),
            }
            for d in timeline_days
        ]

        completed_interviews_chart = [
            {
                "date": d.isoformat(),
                "count": comp_int_map.get(d, 0),
                "value": comp_int_map.get(d, 0),
            }
            for d in timeline_days
        ]

        revenue_chart = [
            {
                "date": d.isoformat(),
                "count": int((rev_chart_map.get(d, 0) or 0) / 100.0),
                "value": round(float(rev_chart_map.get(d, 0) or 0) / 100.0, 2),
                "secondary": round(float(rev_chart_map.get(d, 0) or 0) / 100.0, 2),
            }
            for d in timeline_days
        ]

        support_tickets_chart = [
            {
                "date": d.isoformat(),
                "count": supp_chart_map.get(d, 0),
                "value": supp_chart_map.get(d, 0),
            }
            for d in timeline_days
        ]

        # ----------------------------------------------------
        # DISTRIBUTIONS & RECENT LISTS
        # ----------------------------------------------------
        role_dist_res = await db.execute(
            select(Interview.job_role, func.count(Interview.id))
            .group_by(Interview.job_role)
            .order_by(desc(func.count(Interview.id)))
            .limit(5)
        )
        role_distribution = [
            {"category": row[0] or "General", "count": row[1]}
            for row in role_dist_res.all()
        ]

        diff_dist_res = await db.execute(
            select(Interview.difficulty, func.count(Interview.id))
            .group_by(Interview.difficulty)
            .order_by(desc(func.count(Interview.id)))
        )
        difficulty_distribution = [
            {"category": row[0] or "Medium", "count": row[1]}
            for row in diff_dist_res.all()
        ]

        recent_u_res = await db.execute(
            select(User).order_by(desc(User.created_at)).limit(5)
        )
        recent_registrations = [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name or "N/A",
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in recent_u_res.scalars().all()
        ]

        recent_int_res = await db.execute(
            select(Interview, User.email)
            .join(User, Interview.user_id == User.id, isouter=True)
            .order_by(desc(Interview.created_at))
            .limit(5)
        )
        recent_interviews = [
            {
                "id": str(item[0].id),
                "user_email": item[1] or "Unknown",
                "job_role": item[0].job_role,
                "difficulty": item[0].difficulty,
                "status": item[0].status,
                "score": item[0].score,
                "created_at": item[0].created_at.isoformat(),
            }
            for item in recent_int_res.all()
        ]

        recent_pay_res = await db.execute(
            select(PaymentTransaction, User.email)
            .join(User, PaymentTransaction.user_id == User.id, isouter=True)
            .order_by(desc(PaymentTransaction.created_at))
            .limit(5)
        )
        recent_payments = [
            {
                "id": str(item[0].id),
                "order_id": item[0].provider_order_id or "N/A",
                "user_email": item[1] or "Unknown",
                "amount": round(float(item[0].amount) / 100.0, 2),
                "status": item[0].status,
                "created_at": item[0].created_at.isoformat(),
            }
            for item in recent_pay_res.all()
        ]

        recent_tick_res = await db.execute(
            select(SupportTicket).order_by(desc(SupportTicket.created_at)).limit(5)
        )
        recent_tickets = [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in recent_tick_res.scalars().all()
        ]

        audit_res = await db.execute(
            select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(10)
        )
        recent_activities = [
            {
                "id": str(log.id),
                "action": log.action,
                "actor_email": log.actor_email,
                "resource_type": log.resource,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "details": log.details,
                "timestamp": log.created_at.isoformat(),
                "created_at": log.created_at.isoformat(),
            }
            for log in audit_res.scalars().all()
        ]

        # ----------------------------------------------------
        # STRUCTURED KPI & TREND DICTIONARIES
        # ----------------------------------------------------
        kpis_dict = {
            "total_users": total_users,
            "active_users": active_users,
            "new_users": new_users_in_range,
            "new_users_last_7_days": new_users_7d,
            "new_users_30d": new_users_30d,
            "total_interviews": total_interviews,
            "completed_interviews": completed_interviews,
            "average_interview_score": avg_interview_score,
            "avg_interview_score": avg_interview_score,
            "average_ats_score": avg_ats_score,
            "avg_ats_score": avg_ats_score,
            "active_subscriptions": active_subscriptions,
            "active_subscription_users": active_subscriptions,
            "total_subscription_plans": total_subscription_plans,
            "expired_subscriptions": expired_subscriptions,
            "cancelled_subscriptions": cancelled_subscriptions,
            "pending_subscriptions": pending_subscriptions,
            "total_revenue_inr": total_revenue_inr,
            "revenue": total_revenue_inr,
            "total_payment_transactions": total_payment_transactions,
            "payment_transactions_count": total_payment_transactions,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "pending_payments": pending_payments,
            "pending_support_tickets": pending_support_tickets,
            "open_support_tickets": open_support_tickets,
            "total_support_tickets": total_support_tickets,
            "support_tickets_total": total_support_tickets,
            "in_progress_support_tickets": in_progress_support_tickets,
            "resolved_support_tickets": resolved_support_tickets,
            "closed_support_tickets": closed_support_tickets,
            "technical_questions": technical_questions,
            "coding_problems": coding_problems,
            "total_coding_submissions": total_coding_submissions,
            "contests": contests,
            "contest_participants": contest_participants,
            "rag_question_count": rag_question_count,
            "rag_indexed_questions": rag_question_count,
        }

        trends_dict = {
            "interviews_daily": interview_activity_chart,
            "completed_interviews_daily": completed_interviews_chart,
            "user_registrations_daily": user_growth_chart,
            "revenue_daily": revenue_chart,
            "support_tickets_daily": support_tickets_chart,
        }

        payload = {
            **kpis_dict,
            "user_growth_chart": user_growth_chart,
            "interview_activity_chart": interview_activity_chart,
            "revenue_chart": revenue_chart,
            "role_distribution": role_distribution,
            "difficulty_distribution": difficulty_distribution,
            "recent_registrations": recent_registrations,
            "recent_interviews": recent_interviews,
            "recent_payments": recent_payments,
            "recent_tickets": recent_tickets,
            "recent_activities": recent_activities,
            "kpis": kpis_dict,
            "trends": trends_dict,
        }
        return payload

    # ============================================================
    # 3. USER MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """List users with pagination, search, and filtering."""
        query = select(User)

        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.email.ilike(search_clean),
                    User.full_name.ilike(search_clean),
                )
            )
        if role:
            query = query.where(User.role == role.upper())
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(User.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        users = result.scalars().all()

        user_items = []
        for u in users:
            # Interview stats
            int_stats = await db.execute(
                select(func.count(Interview.id), func.avg(Interview.score)).where(
                    Interview.user_id == u.id
                )
            )
            int_row = int_stats.first()
            int_count = int_row[0] if int_row else 0
            avg_score = round(float(int_row[1]), 1) if int_row and int_row[1] else None

            # Coding count
            code_res = await db.execute(
                select(func.count(CodingSubmission.id)).where(
                    CodingSubmission.user_id == u.id
                )
            )
            coding_count = code_res.scalar() or 0

            # Subscription status
            sub_res = await db.execute(
                select(SubscriptionPlan.name)
                .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
                .where(
                    and_(
                        UserSubscription.user_id == u.id,
                        UserSubscription.status == "active",
                    )
                )
            )
            sub_code = sub_res.scalar_one_or_none() or "FREE"

            user_items.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "is_verified": u.is_verified,
                    "created_at": u.created_at,
                    "interview_count": int_count,
                    "avg_score": avg_score,
                    "coding_count": coding_count,
                    "subscription_status": sub_code,
                }
            )

        return {
            "users": user_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_user_detail(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Get complete user details without exposing passwords/secrets."""
        u_res = await db.execute(select(User).where(User.id == user_id))
        user = u_res.scalar_one_or_none()
        if not user:
            return None

        # Profile
        prof_res = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = prof_res.scalar_one_or_none()
        prof_data = None
        if profile:
            prof_data = {
                "headline": profile.headline,
                "phone": profile.phone,
                "bio": profile.bio,
                "skills": profile.skills,
                "target_role": profile.target_role,
                "experience_level": profile.experience_level,
                "education": profile.education,
                "location": profile.location,
            }

        # Interview History
        int_res = await db.execute(
            select(Interview)
            .where(Interview.user_id == user_id)
            .order_by(desc(Interview.created_at))
            .limit(10)
        )
        interviews = [
            {
                "id": str(i.id),
                "job_role": i.job_role,
                "difficulty": i.difficulty,
                "status": i.status,
                "score": i.score,
                "created_at": i.created_at.isoformat(),
            }
            for i in int_res.scalars().all()
        ]

        # Coding statistics
        total_code_res = await db.execute(
            select(func.count(CodingSubmission.id)).where(
                CodingSubmission.user_id == user_id
            )
        )
        passed_code_res = await db.execute(
            select(func.count(CodingSubmission.id)).where(
                and_(
                    CodingSubmission.user_id == user_id,
                    CodingSubmission.status == "accepted",
                )
            )
        )
        total_sub = total_code_res.scalar() or 0
        accepted_sub = passed_code_res.scalar() or 0
        coding_stats = {
            "total_submissions": total_sub,
            "accepted_submissions": accepted_sub,
            "acceptance_rate": round((accepted_sub / total_sub * 100), 1)
            if total_sub
            else 0.0,
        }

        # Subscription
        sub_res = await db.execute(
            select(UserSubscription, SubscriptionPlan.name)
            .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
            .where(
                and_(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == "active",
                )
            )
        )
        active_sub_row = sub_res.first()
        sub_data = None
        if active_sub_row:
            active_sub, plan_name = active_sub_row
            sub_data = {
                "plan_code": plan_name,
                "status": active_sub.status,
                "start_date": active_sub.starts_at.isoformat() if active_sub.starts_at else None,
                "end_date": active_sub.expires_at.isoformat() if active_sub.expires_at else None,
            }

        # Support Tickets
        tick_res = await db.execute(
            select(SupportTicket)
            .where(SupportTicket.user_id == user_id)
            .order_by(desc(SupportTicket.created_at))
            .limit(5)
        )
        tickets = [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in tick_res.scalars().all()
        ]

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "profile": prof_data,
            "interview_history": interviews,
            "coding_stats": coding_stats,
            "subscription": sub_data,
            "support_tickets": tickets,
        }

    @staticmethod
    async def update_user_status(
        db: AsyncSession,
        user_id: uuid.UUID,
        is_active: bool,
        actor: User,
    ) -> bool:
        """Activate or deactivate user account."""
        res = await db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            return False

        old_status = user.is_active
        user.is_active = is_active
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="USER_STATUS_CHANGE",
            resource="user",
            resource_id=str(user.id),
            details={"old_status": old_status, "new_status": is_active},
        )
        return True

    @staticmethod
    async def update_user_role(
        db: AsyncSession,
        user_id: uuid.UUID,
        role: str,
        actor: User,
    ) -> bool:
        """Change user role with protection against super admin self-demotion."""
        res = await db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            return False

        # Prevent Super Admin from demoting themselves if they are the only Super Admin
        if user.id == actor.id and user.role == "SUPER_ADMIN" and role != "SUPER_ADMIN":
            count_sa = await db.execute(
                select(func.count(User.id)).where(User.role == "SUPER_ADMIN")
            )
            if (count_sa.scalar() or 0) <= 1:
                raise ValueError("Cannot remove your own final Super Admin role.")

        old_role = user.role
        user.role = role.upper()
        user.is_admin = role.upper() in [
            "SUPER_ADMIN",
            "ADMIN",
            "INTERVIEW_ADMIN",
            "CONTENT_ADMIN",
            "AI_ADMIN",
            "FINANCE_ADMIN",
            "SUPPORT_ADMIN",
            "ANALYTICS_ADMIN",
        ]
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="USER_ROLE_CHANGE",
            resource="user",
            resource_id=str(user.id),
            details={"old_role": old_role, "new_role": user.role},
        )
        return True

    # ============================================================
    # 4. INTERVIEW MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_interviews(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        job_role: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List candidate interviews with pagination and search filters."""
        query = select(Interview, User.email, User.full_name).join(
            User, Interview.user_id == User.id, isouter=True
        )

        if status:
            query = query.where(Interview.status == status.lower())
        if job_role:
            query = query.where(Interview.job_role.ilike(f"%{job_role}%"))
        if difficulty:
            query = query.where(Interview.difficulty.ilike(f"%{difficulty}%"))
        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.email.ilike(search_clean),
                    User.full_name.ilike(search_clean),
                    Interview.job_role.ilike(search_clean),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Interview.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": r[0].id,
                "user_id": r[0].user_id,
                "user_email": r[1] or "Unknown",
                "user_name": r[2] or "N/A",
                "job_role": r[0].job_role,
                "difficulty": r[0].difficulty,
                "status": r[0].status,
                "score": r[0].score,
                "started_at": r[0].started_at,
                "completed_at": r[0].completed_at,
                "created_at": r[0].created_at,
            }
            for r in rows
        ]

        return {
            "interviews": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_interview_detail(
        db: AsyncSession,
        interview_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Get complete interview evaluation, transcript, and anti-cheating logs."""
        res = await db.execute(
            select(Interview, User.email)
            .join(User, Interview.user_id == User.id, isouter=True)
            .where(Interview.id == interview_id)
        )
        row = res.first()
        if not row:
            return None

        int_obj, user_email = row

        # Parse JSON fields safely if stringified
        def safe_json(val: Any) -> Any:
            if not val:
                return None
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return val

        return {
            "id": int_obj.id,
            "user_id": int_obj.user_id,
            "user_email": user_email,
            "job_role": int_obj.job_role,
            "difficulty": int_obj.difficulty,
            "status": int_obj.status,
            "score": int_obj.score,
            "feedback": int_obj.feedback,
            "strengths": int_obj.strengths,
            "weaknesses": int_obj.weaknesses,
            "transcript": int_obj.transcript,
            "question_evaluations": safe_json(int_obj.question_evaluations),
            "questions": safe_json(int_obj.questions),
            "answers": safe_json(int_obj.answers),
            "created_at": int_obj.created_at,
            "completed_at": int_obj.completed_at,
        }

    # ============================================================
    # 5. QUESTION MANAGEMENT (PRACTICE QUESTIONS)
    # ============================================================
    @staticmethod
    async def list_questions(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        technology: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List technical & practice questions from practice_questions."""
        query = select(PracticeQuestion)
        if technology:
            query = query.where(
                PracticeQuestion.technology.ilike(f"%{technology}%")
            )
        if difficulty:
            query = query.where(
                PracticeQuestion.difficulty.ilike(f"%{difficulty}%")
            )
        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                or_(
                    PracticeQuestion.question.ilike(search_clean),
                    PracticeQuestion.topic.ilike(search_clean),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(PracticeQuestion.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "questions": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def create_question(
        db: AsyncSession,
        data: CreateQuestionRequest,
        actor: User,
    ) -> PracticeQuestion:
        """Create a new technical question."""
        q_id = data.id or f"q_{uuid.uuid4().hex[:12]}"
        tech_slug = data.technology.lower().replace(" ", "-").replace(".", "")
        topic_slug = data.topic.lower().replace(" ", "-").replace(".", "")

        new_q = PracticeQuestion(
            id=q_id,
            technology=data.technology,
            technology_slug=tech_slug,
            topic=data.topic,
            topic_slug=topic_slug,
            subtopic=data.subtopic,
            question=data.question,
            difficulty=data.difficulty,
            question_type=data.question_type,
            role=data.role,
            explanation=data.explanation,
            source="admin_created",
        )
        db.add(new_q)
        await db.commit()
        await db.refresh(new_q)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="QUESTION_CREATE",
            resource="question",
            resource_id=new_q.id,
            details={"technology": new_q.technology, "topic": new_q.topic},
        )
        return new_q

    @staticmethod
    async def update_question(
        db: AsyncSession,
        question_id: str,
        data: UpdateQuestionRequest,
        actor: User,
    ) -> PracticeQuestion | None:
        """Update existing technical question."""
        res = await db.execute(
            select(PracticeQuestion).where(PracticeQuestion.id == question_id)
        )
        q = res.scalar_one_or_none()
        if not q:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(q, k, v)
        if "technology" in update_data and update_data["technology"]:
            q.technology_slug = (
                update_data["technology"]
                .lower()
                .replace(" ", "-")
                .replace(".", "")
            )
        if "topic" in update_data and update_data["topic"]:
            q.topic_slug = (
                update_data["topic"].lower().replace(" ", "-").replace(".", "")
            )

        q.updated_at = utc_now()
        await db.commit()
        await db.refresh(q)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="QUESTION_UPDATE",
            resource="question",
            resource_id=q.id,
            details={"fields": list(update_data.keys())},
        )
        return q

    @staticmethod
    async def delete_question(
        db: AsyncSession,
        question_id: str,
        actor: User,
    ) -> bool:
        """Delete technical question."""
        res = await db.execute(
            select(PracticeQuestion).where(PracticeQuestion.id == question_id)
        )
        q = res.scalar_one_or_none()
        if not q:
            return False

        await db.delete(q)
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="QUESTION_DELETE",
            resource="question",
            resource_id=question_id,
        )
        return True

    # ============================================================
    # 6. COMPANY MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_companies(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        industry: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List target company profiles with search and industry filter."""
        query = select(Company)
        if industry:
            query = query.where(Company.industry.ilike(f"%{industry}%"))
        if search:
            query = query.where(Company.name.ilike(f"%{search.strip()}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Company.name.asc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "companies": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def create_company(
        db: AsyncSession,
        data: CreateCompanyRequest,
        actor: User,
    ) -> Company:
        """Create target company profile."""
        company = Company(
            name=data.name.strip(),
            logo_url=data.logo_url,
            description=data.description,
            industry=data.industry,
            website=data.website,
            roles=data.roles or [],
            interview_types=data.interview_types or [],
            difficulty=data.difficulty,
            preparation_content=data.preparation_content,
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="COMPANY_CREATE",
            resource="company",
            resource_id=str(company.id),
            details={"name": company.name},
        )
        return company

    @staticmethod
    async def update_company(
        db: AsyncSession,
        company_id: uuid.UUID,
        data: UpdateCompanyRequest,
        actor: User,
    ) -> Company | None:
        """Update company profile."""
        res = await db.execute(select(Company).where(Company.id == company_id))
        company = res.scalar_one_or_none()
        if not company:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(company, k, v)
        company.updated_at = utc_now()

        await db.commit()
        await db.refresh(company)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="COMPANY_UPDATE",
            resource="company",
            resource_id=str(company.id),
            details={"fields": list(update_data.keys())},
        )
        return company

    @staticmethod
    async def delete_company(
        db: AsyncSession,
        company_id: uuid.UUID,
        actor: User,
    ) -> bool:
        """Archive company profile."""
        res = await db.execute(select(Company).where(Company.id == company_id))
        company = res.scalar_one_or_none()
        if not company:
            return False

        company.is_active = not company.is_active
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="COMPANY_STATUS_TOGGLE",
            resource="company",
            resource_id=str(company.id),
            details={"is_active": company.is_active},
        )
        return True

    # ============================================================
    # 7. RESOURCE MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_resources(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        topic: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List curated learning resources."""
        query = select(LearningResource)
        if topic:
            query = query.where(LearningResource.topic.ilike(f"%{topic}%"))
        if search:
            query = query.where(
                LearningResource.title.ilike(f"%{search.strip()}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(LearningResource.title.asc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "resources": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def create_resource(
        db: AsyncSession,
        data: CreateResourceRequest,
        actor: User,
    ) -> LearningResource:
        """Create new learning resource."""
        res = LearningResource(
            title=data.title.strip(),
            description=data.description,
            topic=data.topic,
            canonical_skill=data.canonical_skill,
            difficulty=data.difficulty,
            resource_type=data.resource_type,
            url=data.url,
        )
        db.add(res)
        await db.commit()
        await db.refresh(res)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="RESOURCE_CREATE",
            resource="resource",
            resource_id=str(res.id),
            details={"title": res.title},
        )
        return res

    @staticmethod
    async def update_resource(
        db: AsyncSession,
        resource_id: uuid.UUID,
        data: UpdateResourceRequest,
        actor: User,
    ) -> LearningResource | None:
        """Update existing learning resource."""
        res_stmt = await db.execute(
            select(LearningResource).where(LearningResource.id == resource_id)
        )
        res_obj = res_stmt.scalar_one_or_none()
        if not res_obj:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(res_obj, k, v)

        await db.commit()
        await db.refresh(res_obj)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="RESOURCE_UPDATE",
            resource="resource",
            resource_id=str(res_obj.id),
            details={"fields": list(update_data.keys())},
        )
        return res_obj

    @staticmethod
    async def delete_resource(
        db: AsyncSession,
        resource_id: uuid.UUID,
        actor: User,
    ) -> bool:
        """Delete learning resource."""
        res_stmt = await db.execute(
            select(LearningResource).where(LearningResource.id == resource_id)
        )
        res_obj = res_stmt.scalar_one_or_none()
        if not res_obj:
            return False

        await db.delete(res_obj)
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="RESOURCE_DELETE",
            resource="resource",
            resource_id=str(resource_id),
        )
        return True

    # ============================================================
    # 8. AI AGENT MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_ai_agents(db: AsyncSession) -> list[AIAgentConfig]:
        """List AI agents without exposing secret credentials."""
        res = await db.execute(
            select(AIAgentConfig).order_by(AIAgentConfig.name.asc())
        )
        return res.scalars().all()

    @staticmethod
    async def update_ai_agent(
        db: AsyncSession,
        agent_id: uuid.UUID,
        data: UpdateAIAgentConfigRequest,
        actor: User,
    ) -> AIAgentConfig | None:
        """Update agent configurations (temperature, token limits, system prompts)."""
        res = await db.execute(
            select(AIAgentConfig).where(AIAgentConfig.id == agent_id)
        )
        agent = res.scalar_one_or_none()
        if not agent:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(agent, k, v)
        agent.updated_at = utc_now()

        await db.commit()
        await db.refresh(agent)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="AI_AGENT_CONFIG_UPDATE",
            resource="ai_agent",
            resource_id=agent.agent_key,
            details={"updated_fields": list(update_data.keys())},
        )
        return agent

    # ============================================================
    # 9. RESUME / ATS MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_resumes(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List resumes with candidate details and upload status."""
        query = select(Resume, User.email, User.full_name).join(
            User, Resume.user_id == User.id, isouter=True
        )
        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.email.ilike(search_clean),
                    Resume.filename.ilike(search_clean),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Resume.uploaded_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": r[0].id,
                "user_id": r[0].user_id,
                "user_email": r[1] or "Unknown",
                "user_name": r[2] or "N/A",
                "filename": r[0].filename,
                "file_url": r[0].file_url,
                "uploaded_at": r[0].uploaded_at,
            }
            for r in rows
        ]

        return {
            "resumes": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ============================================================
    # 10. SUBSCRIPTIONS, PAYMENTS, COUPONS, INVOICES
    # ============================================================
    @staticmethod
    async def list_subscription_plans(
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """List subscription plans."""
        res = await db.execute(
            select(SubscriptionPlan).order_by(SubscriptionPlan.price.asc())
        )
        plans = res.scalars().all()
        return [
            {
                "id": p.id,
                "plan_code": p.slug,
                "name": p.name,
                "description": p.description,
                "price_inr": round(float(p.price) / 100.0, 2),
                "duration_days": p.duration_days,
                "interview_limit": (p.limits or {}).get("ai_interviews", 10),
                "resume_analyses_limit": (p.limits or {}).get("resume_analyses", 5),
                "coding_practice_unlimited": True,
                "is_active": p.is_active,
            }
            for p in plans
        ]

    @staticmethod
    async def create_subscription_plan(
        db: AsyncSession,
        data: CreateSubscriptionPlanRequest,
        actor: User,
    ) -> dict[str, Any]:
        """Create new subscription plan."""
        plan = SubscriptionPlan(
            name=data.name.strip(),
            slug=data.plan_code.lower().strip(),
            description=data.description,
            price=int(data.price_inr * 100),
            currency="INR",
            duration_days=data.duration_days,
            is_active=data.is_active,
            features=["AI Interviews", "ATS Resume", "Coding Arena"],
            limits={
                "ai_interviews": data.interview_limit,
                "resume_analyses": data.resume_analyses_limit,
            },
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="SUBSCRIPTION_PLAN_CREATE",
            resource="subscription_plan",
            resource_id=plan.slug,
            details={"price_inr": data.price_inr},
        )
        return {
            "id": plan.id,
            "plan_code": plan.slug,
            "name": plan.name,
            "description": plan.description,
            "price_inr": data.price_inr,
            "duration_days": plan.duration_days,
            "interview_limit": data.interview_limit,
            "resume_analyses_limit": data.resume_analyses_limit,
            "coding_practice_unlimited": data.coding_practice_unlimited,
            "is_active": plan.is_active,
        }

    @staticmethod
    async def list_payments(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List payment transactions with order IDs and user email without secrets."""
        query = select(PaymentTransaction, User.email, SubscriptionPlan.name).join(
            User, PaymentTransaction.user_id == User.id, isouter=True
        ).join(
            SubscriptionPlan, PaymentTransaction.plan_id == SubscriptionPlan.id, isouter=True
        )
        if status:
            query = query.where(PaymentTransaction.status == status.lower())
        if search:
            search_clean = f"%{search.strip()}%"
            query = query.where(
                or_(
                    PaymentTransaction.provider_order_id.ilike(search_clean),
                    PaymentTransaction.provider_payment_id.ilike(search_clean),
                    User.email.ilike(search_clean),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(PaymentTransaction.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": r[0].id,
                "user_id": r[0].user_id,
                "user_email": r[1] or "Unknown",
                "plan_code": r[2] or "Plan",
                "amount_inr": round(float(r[0].amount) / 100.0, 2),
                "currency": r[0].currency,
                "status": r[0].status,
                "order_id": r[0].provider_order_id or "N/A",
                "payment_id": r[0].provider_payment_id,
                "created_at": r[0].created_at,
            }
            for r in rows
        ]

        return {
            "payments": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def list_coupons(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List coupons with usage counters."""
        query = select(Coupon)
        count_query = select(func.count(Coupon.id))
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Coupon.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        coupon_items = [
            {
                "id": c.id,
                "code": c.code,
                "discount_type": c.discount_type,
                "discount_value": c.discount_value,
                "max_discount_inr": round(float(c.max_discount) / 100.0, 2) if c.max_discount else None,
                "min_order_inr": round(float(c.minimum_amount) / 100.0, 2) if c.minimum_amount else 0.0,
                "valid_from": c.valid_from,
                "valid_until": c.valid_until,
                "usage_limit": c.usage_limit,
                "times_used": c.used_count,
                "is_active": c.is_active,
            }
            for c in items
        ]

        return {
            "coupons": coupon_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def create_coupon(
        db: AsyncSession,
        data: CreateCouponRequest,
        actor: User,
    ) -> dict[str, Any]:
        """Create discount coupon."""
        coupon = Coupon(
            code=data.code.upper().strip(),
            discount_type=data.discount_type.lower(),
            discount_value=int(data.discount_value),
            max_discount=int(data.max_discount_inr * 100) if data.max_discount_inr else None,
            minimum_amount=int(data.min_order_inr * 100) if data.min_order_inr else 0,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            usage_limit=data.usage_limit,
            used_count=0,
            is_active=True,
        )
        db.add(coupon)
        await db.commit()
        await db.refresh(coupon)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="COUPON_CREATE",
            resource="coupon",
            resource_id=coupon.code,
            details={"discount_value": coupon.discount_value},
        )
        return {
            "id": coupon.id,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "max_discount_inr": round(float(coupon.max_discount) / 100.0, 2) if coupon.max_discount else None,
            "min_order_inr": round(float(coupon.minimum_amount) / 100.0, 2) if coupon.minimum_amount else 0.0,
            "valid_from": coupon.valid_from,
            "valid_until": coupon.valid_until,
            "usage_limit": coupon.usage_limit,
            "times_used": coupon.used_count,
            "is_active": coupon.is_active,
        }

    @staticmethod
    async def toggle_coupon_status(
        db: AsyncSession,
        coupon_id: uuid.UUID,
        actor: User,
    ) -> bool:
        """Activate or deactivate coupon."""
        res = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
        coupon = res.scalar_one_or_none()
        if not coupon:
            return False

        coupon.is_active = not coupon.is_active
        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="COUPON_STATUS_TOGGLE",
            resource="coupon",
            resource_id=coupon.code,
            details={"is_active": coupon.is_active},
        )
        return True

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List generated candidate invoices."""
        query = select(Invoice, User.email).join(
            User, Invoice.user_id == User.id, isouter=True
        )
        count_query = select(func.count(Invoice.id))
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Invoice.issued_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": r[0].id,
                "invoice_number": r[0].invoice_number,
                "user_id": r[0].user_id,
                "user_email": r[1] or "Unknown",
                "plan_name": "Subscription",
                "subtotal_inr": round(float(r[0].amount) / 100.0, 2),
                "tax_inr": round(float(r[0].tax) / 100.0, 2),
                "discount_inr": round(float(r[0].discount) / 100.0, 2),
                "total_inr": round(float(r[0].total_amount) / 100.0, 2),
                "status": r[0].status,
                "created_at": r[0].issued_at,
            }
            for r in rows
        ]

        return {
            "invoices": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ============================================================
    # 11. FEEDBACK & BUG REPORTS
    # ============================================================
    @staticmethod
    async def list_feedback(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List candidate feedback and bug reports."""
        query = select(Feedback, User.email).join(
            User, Feedback.user_id == User.id, isouter=True
        )
        if category:
            query = query.where(Feedback.category == category.lower())
        if status:
            query = query.where(Feedback.status == status.lower())

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Feedback.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": r[0].id,
                "user_id": r[0].user_id,
                "user_email": r[1] or "Unknown",
                "category": r[0].category,
                "rating": r[0].rating,
                "message": r[0].message,
                "page_context": r[0].page_context,
                "status": r[0].status,
                "created_at": r[0].created_at,
            }
            for r in rows
        ]

        return {
            "feedback": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def update_feedback_status(
        db: AsyncSession,
        feedback_id: uuid.UUID,
        new_status: str,
        notes: str | None,
        actor: User,
    ) -> bool:
        """Update resolution status on candidate feedback."""
        res = await db.execute(
            select(Feedback).where(Feedback.id == feedback_id)
        )
        fb = res.scalar_one_or_none()
        if not fb:
            return False

        old_status = fb.status
        fb.status = new_status.lower()
        if notes:
            meta = dict(fb.metadata_json or {})
            meta["resolution_notes"] = notes
            meta["resolved_by"] = actor.email
            fb.metadata_json = meta

        await db.commit()

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="FEEDBACK_STATUS_CHANGE",
            resource="feedback",
            resource_id=str(fb.id),
            details={"old_status": old_status, "new_status": fb.status},
        )
        return True

    # ============================================================
    # 12. NOTIFICATION BROADCAST (POSTGRESQL + WEBSOCKET)
    # ============================================================
    @staticmethod
    async def broadcast_notification(
        db: AsyncSession,
        data: BroadcastNotificationRequest,
        actor: User,
    ) -> int:
        """Persist notifications to PostgreSQL and broadcast via Phase 16 WebSocket."""
        # Find target users
        target_query = select(User).where(User.is_active == True)
        if data.target_role:
            target_query = target_query.where(
                User.role == data.target_role.upper()
            )

        res = await db.execute(target_query)
        target_users = res.scalars().all()
        created_count = 0

        for u in target_users:
            notif = Notification(
                user_id=u.id,
                title=data.title,
                message=data.message,
                type=data.type,
                action_url=data.link,
                icon="📢",
                metadata_json={},
                is_read=False,
            )
            db.add(notif)
            created_count += 1

        await db.commit()

        # Publish WebSocket event to target audience
        ws_payload = {
            "type": data.type,
            "title": data.title,
            "message": data.message,
            "link": data.link,
            "created_at": utc_now().isoformat(),
        }

        if data.target_role:
            await publish_event(
                event_type=WebSocketEventType.NOTIFICATION_CREATED,
                data=ws_payload,
                role=data.target_role.lower(),
            )
        else:
            await publish_event(
                event_type=WebSocketEventType.SYSTEM_EVENT,
                data=ws_payload,
                is_broadcast=True,
            )

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="NOTIFICATION_BROADCAST",
            resource="notification",
            details={
                "title": data.title,
                "target_role": data.target_role,
                "count": created_count,
            },
        )
        return created_count

    # ============================================================
    # 13. ACHIEVEMENTS MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_achievements(
        db: AsyncSession,
    ) -> list[AchievementDefinition]:
        """List achievement badges and unlock criteria."""
        res = await db.execute(
            select(AchievementDefinition).order_by(
                AchievementDefinition.sort_order.asc()
            )
        )
        return res.scalars().all()

    @staticmethod
    async def create_achievement(
        db: AsyncSession,
        data: CreateAchievementRequest,
        actor: User,
    ) -> AchievementDefinition:
        """Create new achievement badge definition."""
        ach = AchievementDefinition(
            id=data.id.lower().replace(" ", "_"),
            name=data.name.strip(),
            description=data.description,
            category=data.category,
            icon=data.icon,
            rarity=data.rarity,
            xp_reward=data.xp_reward,
            target_value=data.target_value,
            is_active=data.is_active,
        )
        db.add(ach)
        await db.commit()
        await db.refresh(ach)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="ACHIEVEMENT_CREATE",
            resource="achievement",
            resource_id=ach.id,
            details={"name": ach.name, "xp": ach.xp_reward},
        )
        return ach

    # ============================================================
    # 14. AUDIT LOGS RETRIEVAL
    # ============================================================
    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 30,
        action: str | None = None,
        resource: str | None = None,
        actor_email: str | None = None,
    ) -> dict[str, Any]:
        """Query immutable audit log history."""
        query = select(AdminAuditLog)
        if action:
            query = query.where(AdminAuditLog.action == action.upper())
        if resource:
            query = query.where(AdminAuditLog.resource == resource.lower())
        if actor_email:
            query = query.where(
                AdminAuditLog.actor_email.ilike(f"%{actor_email.strip()}%")
            )

        count_query = select(func.count(AdminAuditLog.id)).select_from(
            query.subquery()
        )
        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(AdminAuditLog.created_at))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "audit_logs": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ============================================================
    # 15. SYSTEM SETTINGS
    # ============================================================
    @staticmethod
    async def list_settings(db: AsyncSession) -> list[SystemSetting]:
        """List platform settings."""
        res = await db.execute(
            select(SystemSetting).order_by(
                SystemSetting.category.asc(), SystemSetting.key.asc()
            )
        )
        return res.scalars().all()

    @staticmethod
    async def update_setting(
        db: AsyncSession,
        key: str,
        value: dict[str, Any],
        actor: User,
    ) -> SystemSetting | None:
        """Update system setting with validation and audit logging."""
        res = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = res.scalar_one_or_none()
        if not setting:
            return None

        old_val = setting.value
        setting.value = value
        setting.updated_by = actor.email
        setting.updated_at = utc_now()

        await db.commit()
        await db.refresh(setting)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="SYSTEM_SETTING_UPDATE",
            resource="system_setting",
            resource_id=key,
            details={"old": old_val, "new": value},
        )
        return setting

    # ============================================================
    # 16. RBAC MANAGEMENT
    # ============================================================
    @staticmethod
    async def list_roles(db: AsyncSession) -> list[AdminRole]:
        """List roles and permissions."""
        res = await db.execute(
            select(AdminRole).order_by(AdminRole.name.asc())
        )
        return res.scalars().all()

    @staticmethod
    async def update_role_permissions(
        db: AsyncSession,
        role_name: str,
        permissions: list[str],
        actor: User,
    ) -> AdminRole | None:
        """Update permissions assigned to an administrative role."""
        role_clean = role_name.upper().strip()
        # Super admin permissions cannot be reduced
        if role_clean == "SUPER_ADMIN":
            raise ValueError(
                "Super Admin role permissions are immutable and complete."
            )

        res = await db.execute(
            select(AdminRole).where(AdminRole.name == role_clean)
        )
        role_obj = res.scalar_one_or_none()
        if not role_obj:
            return None

        old_perms = role_obj.permissions
        # Filter only valid permissions
        valid_perms = [p for p in permissions if p in ALL_PERMISSIONS]
        role_obj.permissions = valid_perms
        role_obj.updated_at = utc_now()

        await db.commit()
        await db.refresh(role_obj)

        await AdminService.log_audit(
            db=db,
            actor=actor,
            action="ROLE_PERMISSIONS_UPDATE",
            resource="role",
            resource_id=role_clean,
            details={"old_count": len(old_perms), "new_count": len(valid_perms)},
        )
        return role_obj

    # ============================================================
    # 17. RAG, LEARNING & CONTESTS STATUS
    # ============================================================
    @staticmethod
    async def get_rag_status(db: AsyncSession) -> dict[str, Any]:
        """Inspect RAG indexing health and category distribution."""
        total_vectors_res = await db.execute(
            select(func.count(InterviewQuestionVector.id))
        )
        total_vectors = total_vectors_res.scalar() or 0

        # Unique roles / categories in vectors
        roles_res = await db.execute(
            select(func.count(func.distinct(InterviewQuestionVector.role)))
        )
        roles_count = roles_res.scalar() or 0

        # Sample topics
        sample_res = await db.execute(
            select(InterviewQuestionVector.role)
            .distinct()
            .limit(5)
        )
        sample_roles = [r[0] for r in sample_res.all() if r[0]]

        return {
            "total_vectors": total_vectors,
            "indexed_questions": total_vectors,
            "categories_count": roles_count,
            "health_status": "HEALTHY" if total_vectors > 0 else "EMPTY",
            "sample_topics": sample_roles or ["Full Stack Developer", "Data Scientist", "DevOps"],
        }

    @staticmethod
    async def get_learning_stats(db: AsyncSession) -> dict[str, Any]:
        """Aggregate learning profile readiness and weak topic signals."""
        prof_res = await db.execute(
            select(func.count(LearningProfile.id), func.avg(LearningProfile.overall_readiness_score))
        )
        row = prof_res.first()
        total_profiles = row[0] if row else 0
        avg_readiness = round(float(row[1]), 1) if row and row[1] else 0.0

        res_count_stmt = await db.execute(select(func.count(LearningResource.id)))
        total_resources = res_count_stmt.scalar() or 0

        # Weak topics from SkillPerformance
        weak_stmt = await db.execute(
            select(SkillPerformance.canonical_skill, func.count(SkillPerformance.id))
            .where(SkillPerformance.status == "NEEDS_IMPROVEMENT")
            .group_by(SkillPerformance.canonical_skill)
            .order_by(desc(func.count(SkillPerformance.id)))
            .limit(5)
        )
        weak_topics = [
            {"skill": r[0], "count": r[1]} for r in weak_stmt.all()
        ]

        # Popular target roles
        role_stmt = await db.execute(
            select(LearningProfile.target_role, func.count(LearningProfile.id))
            .group_by(LearningProfile.target_role)
            .order_by(desc(func.count(LearningProfile.id)))
            .limit(5)
        )
        popular_skills = [
            {"role": r[0], "count": r[1]} for r in role_stmt.all()
        ]

        return {
            "total_profiles": total_profiles,
            "avg_readiness_score": avg_readiness,
            "total_resources": total_resources,
            "weak_topics": weak_topics,
            "popular_skills": popular_skills,
        }

    # ============================================================
    # 18. INITIAL SYSTEM SEEDER (RUNS ON STARTUP)
    # ============================================================
    @staticmethod
    async def seed_default_admin_data(db: AsyncSession) -> None:
        """Seed default admin roles, system settings, AI agents, and initial super admin."""
        # 1. Seed Roles
        for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            if role_name == "CANDIDATE":
                continue
            res = await db.execute(
                select(AdminRole).where(AdminRole.name == role_name)
            )
            existing = res.scalar_one_or_none()
            if not existing:
                role_obj = AdminRole(
                    name=role_name,
                    description=f"Administrative role for {role_name.replace('_', ' ').title()}",
                    is_system=True,
                    permissions=perms,
                )
                db.add(role_obj)

        # 2. Seed Default AI Agents
        default_agents = [
            {
                "agent_key": "hr_interviewer",
                "name": "HR Behavioral Interviewer",
                "description": "Evaluates cultural fit, leadership, and STAR responses",
                "model_identifier": "gemini-1.5-pro",
                "temperature": 0.7,
                "max_tokens": 2048,
                "system_prompt": "You are an empathetic, professional Senior Talent Acquisition Director conducting a behavioral interview.",
                "feature_assignment": "interview_hr",
            },
            {
                "agent_key": "tech_interviewer",
                "name": "Senior Technical Architect",
                "description": "Probes deep engineering fundamentals, system design, and coding trade-offs",
                "model_identifier": "gemini-1.5-pro",
                "temperature": 0.5,
                "max_tokens": 2048,
                "system_prompt": "You are a Principal Software Engineer conducting a rigorous technical bar raiser interview.",
                "feature_assignment": "interview_tech",
            },
            {
                "agent_key": "evaluation_agent",
                "name": "Objective Assessment Evaluator",
                "description": "Analyzes transcripts and computes rubric-based multidimensional scores",
                "model_identifier": "gemini-1.5-pro",
                "temperature": 0.2,
                "max_tokens": 4096,
                "system_prompt": "You are an expert grading engine that scores candidate responses fairly with detailed constructive feedback.",
                "feature_assignment": "evaluation",
            },
        ]
        for ag in default_agents:
            res = await db.execute(
                select(AIAgentConfig).where(
                    AIAgentConfig.agent_key == ag["agent_key"]
                )
            )
            if not res.scalar_one_or_none():
                db.add(AIAgentConfig(**ag))

        # 3. Seed Default System Settings
        default_settings = [
            {
                "key": "general.platform_name",
                "value": {"name": "AI Interview & Career Platform"},
                "category": "General",
                "description": "Public branding name of the platform",
                "is_sensitive": False,
            },
            {
                "key": "interview.max_duration_minutes",
                "value": {"minutes": 45},
                "category": "Interview",
                "description": "Maximum allowed time for candidate mock interviews",
                "is_sensitive": False,
            },
            {
                "key": "ai.rate_limit_requests_per_minute",
                "value": {"limit": 60},
                "category": "AI",
                "description": "Maximum AI model requests per minute per user",
                "is_sensitive": False,
            },
            {
                "key": "features.enable_voice_interview",
                "value": {"enabled": True},
                "category": "Feature Flags",
                "description": "Toggle browser-based voice interview speech synthesis",
                "is_sensitive": False,
            },
            {
                "key": "security.session_timeout_hours",
                "value": {"hours": 24},
                "category": "Security",
                "description": "JWT session expiration window",
                "is_sensitive": False,
            },
        ]
        for st in default_settings:
            res = await db.execute(
                select(SystemSetting).where(SystemSetting.key == st["key"])
            )
            if not res.scalar_one_or_none():
                db.add(SystemSetting(**st))

        # 4. Ensure Super Admin Account Exists
        admin_email = "admin@interviewplatform.ai"
        res_admin = await db.execute(
            select(User).where(User.email == admin_email)
        )
        super_admin_user = res_admin.scalar_one_or_none()
        if not super_admin_user:
            super_admin_user = User(
                email=admin_email,
                full_name="Platform Administrator",
                hashed_password=hash_password("AdminPass123!"),
                is_active=True,
                is_verified=True,
                role="SUPER_ADMIN",
                is_admin=True,
            )
            db.add(super_admin_user)
        else:
            super_admin_user.role = "SUPER_ADMIN"
            super_admin_user.is_admin = True
            super_admin_user.is_active = True

        await db.commit()
        logger.info("Admin default data, roles, and super admin initialized successfully.")
