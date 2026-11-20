import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.coding.contest_model import Contest
from app.modules.coding.model import CodingProblem
from app.modules.admin.permissions import require_permission
from app.modules.admin.schema import (
    AdminAchievementItem,
    AdminAuditLogItem,
    AdminCouponItem,
    AdminFeedbackItem,
    AdminInterviewDetailResponse,
    AdminInterviewListResponse,
    AdminInvoiceItem,
    AdminPaymentItem,
    AdminQuestionItem,
    AdminQuestionListResponse,
    AdminRoleItem,
    AdminSubscriptionPlanItem,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AIAgentConfigItem,
    AssignUserRoleRequest,
    BroadcastNotificationRequest,
    CompanyItem,
    CreateAchievementRequest,
    CreateCompanyRequest,
    CreateCouponRequest,
    CreateQuestionRequest,
    CreateResourceRequest,
    CreateSubscriptionPlanRequest,
    DashboardKPIsResponse,
    LearningResourceItem,
    LearningStatsResponse,
    RAGStatusResponse,
    SystemSettingItem,
    UpdateAIAgentConfigRequest,
    UpdateCompanyRequest,
    UpdateFeedbackStatusRequest,
    UpdateQuestionRequest,
    UpdateResourceRequest,
    UpdateRolePermissionsRequest,
    UpdateSystemSettingRequest,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    CreateContestRequest,
    UpdateContestRequest,
    AddContestProblemRequest,
    CreateCodingProblemRequest,
    UpdateCodingProblemRequest,
    CreatePracticeSetRequest,
    UpdatePracticeSetRequest,
    AddPracticeSetQuestionRequest,
    CreateInterviewConfigRequest,
    UpdateInterviewConfigRequest,
    CreateCareerRoadmapRequest,
    UpdateCareerRoadmapRequest,
    Candidate360Response,
    DashboardConfigSchema,
)
from app.modules.admin.service import AdminService
from app.modules.support.service import (
    add_ticket_message,
    format_ticket_detail,
    get_ticket_by_id,
    list_all_tickets_admin,
    update_ticket_status,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
)


@router.get(
    "/me",
    summary="Get current user profile and administrative clearance",
)
async def get_admin_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name or current_user.email.split("@")[0],
        "role": (current_user.role or "CANDIDATE").upper(),
        "is_admin": getattr(current_user, "is_admin", False) or current_user.role == "SUPER_ADMIN",
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
    }


# ============================================================
# 1. OVERVIEW & KPIS
# ============================================================
@router.get(
    "/dashboard",
    response_model=DashboardKPIsResponse,
    summary="Get aggregated platform KPIs and chart data",
)
async def get_dashboard_overview(
    time_range: str = Query("30d", enum=["today", "7d", "30d", "90d", "this_year", "year", "all"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analytics.view")),
):
    return await AdminService.get_dashboard_kpis(db, time_range=time_range)


# ============================================================
# 2. USER MANAGEMENT
# ============================================================
@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List platform users with search and filtering",
)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    return await AdminService.list_users(
        db, page=page, page_size=page_size, search=search, role=role, is_active=is_active
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Get detailed user profile, interviews, and statistics",
)
async def get_user_detail(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    user_data = await AdminService.get_user_detail(db, user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data


@router.patch(
    "/users/{user_id}/status",
    summary="Activate or deactivate user account",
)
async def update_user_status(
    user_id: uuid.UUID,
    data: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    success = await AdminService.update_user_status(
        db, user_id, is_active=data.is_active, actor=current_user
    )
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User status updated successfully", "is_active": data.is_active}


@router.patch(
    "/users/{user_id}/role",
    summary="Update user role (RBAC)",
)
async def update_user_role(
    user_id: uuid.UUID,
    data: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    try:
        success = await AdminService.update_user_role(
            db, user_id, role=data.role, actor=current_user
        )
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User role updated successfully", "role": data.role.upper()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 3. INTERVIEW MANAGEMENT
# ============================================================
@router.get(
    "/interviews",
    response_model=AdminInterviewListResponse,
    summary="List candidate interviews",
)
async def get_interviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    job_role: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.view")),
):
    return await AdminService.list_interviews(
        db, page=page, page_size=page_size, status=status, job_role=job_role, difficulty=difficulty, search=search
    )


@router.get(
    "/interviews/{interview_id}",
    response_model=AdminInterviewDetailResponse,
    summary="View complete interview evaluations and transcripts",
)
async def get_interview_detail(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.view")),
):
    int_data = await AdminService.get_interview_detail(db, interview_id)
    if not int_data:
        raise HTTPException(status_code=404, detail="Interview not found")
    return int_data


# ============================================================
# 4. QUESTION MANAGEMENT (PRACTICE QUESTIONS)
# ============================================================
@router.get(
    "/questions",
    response_model=AdminQuestionListResponse,
    summary="List practice and technical questions",
)
async def get_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    technology: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.view")),
):
    return await AdminService.list_questions(
        db, page=page, page_size=page_size, technology=technology, difficulty=difficulty, search=search
    )


@router.post(
    "/questions",
    response_model=AdminQuestionItem,
    status_code=201,
    summary="Create technical interview question",
)
async def create_question(
    data: CreateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.create")),
):
    return await AdminService.create_question(db, data, actor=current_user)


@router.put(
    "/questions/{question_id}",
    response_model=AdminQuestionItem,
    summary="Update technical interview question",
)
async def update_question(
    question_id: str,
    data: UpdateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.update")),
):
    q = await AdminService.update_question(db, question_id, data, actor=current_user)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.delete(
    "/questions/{question_id}",
    summary="Delete technical interview question",
)
async def delete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.delete")),
):
    success = await AdminService.delete_question(db, question_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted successfully"}


# ============================================================
# 5. CODING PROBLEMS MANAGEMENT (1,000 PROBLEM BANK)
# ============================================================
@router.get(
    "/coding/problems",
    summary="List coding arena problems for administrative inspection",
)
async def get_coding_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    difficulty: str | None = None,
    topic: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.view")),
):
    query = select(CodingProblem)
    if difficulty:
        query = query.where(CodingProblem.difficulty.ilike(f"%{difficulty}%"))
    if topic:
        query = query.where(CodingProblem.topic.ilike(f"%{topic}%"))
    if search:
        query = query.where(CodingProblem.title.ilike(f"%{search.strip()}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(CodingProblem.id.asc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = (await db.execute(query)).scalars().all()
    problems = [
        {
            "id": str(p.id),
            "title": p.title,
            "difficulty": getattr(p, "difficulty", "Medium"),
            "topic": getattr(p, "topic", "General"),
            "acceptance_rate": 0.0,
            "is_active": getattr(p, "is_published", True),
        }
        for p in rows
    ]
    return {"problems": problems, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/coding/problems/{problem_id}",
    summary="View coding problem details including hidden test cases for admin",
)
async def get_coding_problem_detail(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("questions.view")),
):
    try:
        p_uuid = uuid.UUID(problem_id)
        res = await db.execute(select(CodingProblem).where(CodingProblem.id == p_uuid))
    except (ValueError, TypeError):
        res = await db.execute(select(CodingProblem).where(CodingProblem.slug == problem_id))
    problem = res.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Coding problem not found")
    return {
        "id": str(problem.id),
        "title": problem.title,
        "difficulty": problem.difficulty,
        "topic": problem.topic,
        "description": problem.description,
        "starter_code": problem.starter_code,
        "test_cases": problem.test_cases,
        "solution": getattr(problem, "solution_code", None) or getattr(problem, "editorial", None),
    }


# ============================================================
# 6. COMPANY MANAGEMENT
# ============================================================
@router.get(
    "/companies",
    summary="List target company profiles",
)
async def get_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    industry: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("companies.view")),
):
    return await AdminService.list_companies(
        db, page=page, page_size=page_size, industry=industry, search=search
    )


@router.post(
    "/companies",
    response_model=CompanyItem,
    status_code=201,
    summary="Create target company profile",
)
async def create_company(
    data: CreateCompanyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("companies.manage")),
):
    return await AdminService.create_company(db, data, actor=current_user)


@router.put(
    "/companies/{company_id}",
    response_model=CompanyItem,
    summary="Update company profile",
)
async def update_company(
    company_id: uuid.UUID,
    data: UpdateCompanyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("companies.manage")),
):
    comp = await AdminService.update_company(db, company_id, data, actor=current_user)
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")
    return comp


@router.delete(
    "/companies/{company_id}",
    summary="Archive or toggle company status",
)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("companies.manage")),
):
    success = await AdminService.delete_company(db, company_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company status toggled successfully"}


# ============================================================
# 7. LEARNING RESOURCE MANAGEMENT
# ============================================================
@router.get(
    "/resources",
    summary="List curated learning resources",
)
async def get_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    topic: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("resources.view")),
):
    return await AdminService.list_resources(
        db, page=page, page_size=page_size, topic=topic, search=search
    )


@router.post(
    "/resources",
    response_model=LearningResourceItem,
    status_code=201,
    summary="Create curated learning resource",
)
async def create_resource(
    data: CreateResourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("resources.manage")),
):
    return await AdminService.create_resource(db, data, actor=current_user)


@router.put(
    "/resources/{resource_id}",
    response_model=LearningResourceItem,
    summary="Update learning resource",
)
async def update_resource(
    resource_id: uuid.UUID,
    data: UpdateResourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("resources.manage")),
):
    res_obj = await AdminService.update_resource(db, resource_id, data, actor=current_user)
    if not res_obj:
        raise HTTPException(status_code=404, detail="Resource not found")
    return res_obj


@router.delete(
    "/resources/{resource_id}",
    summary="Delete learning resource",
)
async def delete_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("resources.manage")),
):
    success = await AdminService.delete_resource(db, resource_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"message": "Resource deleted successfully"}


# ============================================================
# 8. AI AGENT CONFIGURATION MANAGEMENT
# ============================================================
@router.get(
    "/ai-agents",
    response_model=list[AIAgentConfigItem],
    summary="List AI Agents and prompts (secrets protected)",
)
async def get_ai_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ai_agents.view")),
):
    return await AdminService.list_ai_agents(db)


@router.put(
    "/ai-agents/{agent_id}",
    response_model=AIAgentConfigItem,
    summary="Update AI Agent model and prompt configurations",
)
async def update_ai_agent(
    agent_id: uuid.UUID,
    data: UpdateAIAgentConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("ai_agents.manage")),
):
    agent = await AdminService.update_ai_agent(db, agent_id, data, actor=current_user)
    if not agent:
        raise HTTPException(status_code=404, detail="AI Agent configuration not found")
    return agent


# ============================================================
# 9. RESUME / ATS MANAGEMENT
# ============================================================
@router.get(
    "/resume-ats",
    summary="List candidate resumes and ATS scoring progress",
)
async def get_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analytics.view")),
):
    return await AdminService.list_resumes(
        db, page=page, page_size=page_size, search=search
    )


# ============================================================
# 10. SUBSCRIPTIONS & PAYMENT MANAGEMENT
# ============================================================
@router.get(
    "/subscriptions/plans",
    response_model=list[AdminSubscriptionPlanItem],
    summary="List subscription plans",
)
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("subscriptions.view")),
):
    return await AdminService.list_subscription_plans(db)


@router.post(
    "/subscriptions/plans",
    response_model=AdminSubscriptionPlanItem,
    status_code=201,
    summary="Create subscription plan",
)
async def create_subscription_plan(
    data: CreateSubscriptionPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("subscriptions.manage")),
):
    return await AdminService.create_subscription_plan(db, data, actor=current_user)


@router.get(
    "/payments",
    summary="List payments with status and order IDs (secrets protected)",
)
async def get_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("payments.view")),
):
    return await AdminService.list_payments(
        db, page=page, page_size=page_size, status=status, search=search
    )


@router.get(
    "/coupons",
    summary="List discount coupons",
)
async def get_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coupons.manage")),
):
    return await AdminService.list_coupons(db, page=page, page_size=page_size)


@router.post(
    "/coupons",
    response_model=AdminCouponItem,
    status_code=201,
    summary="Create coupon",
)
async def create_coupon(
    data: CreateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coupons.manage")),
):
    return await AdminService.create_coupon(db, data, actor=current_user)


@router.patch(
    "/coupons/{coupon_id}/status",
    summary="Toggle coupon active status",
)
async def toggle_coupon(
    coupon_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coupons.manage")),
):
    success = await AdminService.toggle_coupon_status(db, coupon_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return {"message": "Coupon status toggled successfully"}


@router.get(
    "/invoices",
    summary="List candidate invoices",
)
async def get_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("invoices.view")),
):
    return await AdminService.list_invoices(db, page=page, page_size=page_size)


# ============================================================
# 11. SUPPORT & FEEDBACK
# ============================================================
@router.get(
    "/support/tickets",
    summary="List support tickets for admin operations",
)
async def get_admin_support_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("support.view")),
):
    offset = (page - 1) * page_size
    tickets, total = await list_all_tickets_admin(
        db,
        status_filter=status,
        category_filter=category,
        limit=page_size,
        offset=offset,
    )
    return {
        "tickets": [
            {
                "id": t.id,
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in tickets
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/support/tickets/{ticket_id}",
    summary="Get support ticket details including internal notes for admin",
)
async def get_admin_ticket_detail(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("support.view")),
):
    ticket = await get_ticket_by_id(db, ticket_id, user_id=None, is_admin=True)
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    return format_ticket_detail(ticket, is_admin=True)


@router.post(
    "/support/tickets/{ticket_id}/reply",
    summary="Send agent reply to support ticket with internal note option",
)
async def reply_support_ticket(
    ticket_id: uuid.UUID,
    message: str = Query(..., min_length=1),
    is_internal: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("support.manage")),
):
    await add_ticket_message(
        db,
        ticket_id=ticket_id,
        sender_id=current_user.id,
        message=message,
        sender_type="admin",
        is_internal=is_internal,
        is_admin=True,
    )
    ticket = await get_ticket_by_id(db, ticket_id, user_id=None, is_admin=True)
    return format_ticket_detail(ticket, is_admin=True)


@router.patch(
    "/support/tickets/{ticket_id}/status",
    summary="Update support ticket status",
)
async def update_ticket_status_route(
    ticket_id: uuid.UUID,
    status: str = Query(..., pattern="^(open|in_progress|waiting_user|resolved|closed)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("support.manage")),
):
    ticket = await update_ticket_status(
        db, ticket_id, new_status=status, user_id=current_user.id, is_admin=True
    )
    return format_ticket_detail(ticket, is_admin=True)


@router.get(
    "/feedback",
    summary="List user feedback and bug reports",
)
async def get_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("feedback.view")),
):
    return await AdminService.list_feedback(
        db, page=page, page_size=page_size, category=category, status=status
    )


@router.patch(
    "/feedback/{feedback_id}",
    summary="Update feedback resolution status",
)
async def update_feedback_status(
    feedback_id: uuid.UUID,
    data: UpdateFeedbackStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("feedback.manage")),
):
    success = await AdminService.update_feedback_status(
        db, feedback_id, new_status=data.status, notes=data.resolution_notes, actor=current_user
    )
    if not success:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    return {"message": "Feedback status updated successfully"}


# ============================================================
# 12. NOTIFICATION BROADCASTS
# ============================================================
@router.post(
    "/notifications/broadcast",
    summary="Send platform announcement via PostgreSQL persistence + WebSocket",
)
async def broadcast_notification(
    data: BroadcastNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("notifications.manage")),
):
    count = await AdminService.broadcast_notification(db, data, actor=current_user)
    return {"message": "Notification broadcast successfully", "recipients_count": count}


# ============================================================
# 13. ACHIEVEMENTS
# ============================================================
@router.get(
    "/achievements",
    response_model=list[AdminAchievementItem],
    summary="List achievement badges",
)
async def get_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("achievements.manage")),
):
    return await AdminService.list_achievements(db)


@router.post(
    "/achievements",
    response_model=AdminAchievementItem,
    status_code=201,
    summary="Create achievement badge definition",
)
async def create_achievement(
    data: CreateAchievementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("achievements.manage")),
):
    return await AdminService.create_achievement(db, data, actor=current_user)


# ============================================================
# 14. AUDIT LOGS
# ============================================================
@router.get(
    "/audit-logs",
    summary="Query immutable administrative audit logs",
)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: str | None = None,
    resource: str | None = None,
    actor_email: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audit_logs.view")),
):
    return await AdminService.list_audit_logs(
        db, page=page, page_size=page_size, action=action, resource=resource, actor_email=actor_email
    )


# ============================================================
# 15. SYSTEM SETTINGS
# ============================================================
@router.get(
    "/settings",
    response_model=list[SystemSettingItem],
    summary="List system configuration settings",
)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    return await AdminService.list_settings(db)


@router.put(
    "/settings/{key}",
    response_model=SystemSettingItem,
    summary="Update system setting",
)
async def update_setting(
    key: str,
    data: UpdateSystemSettingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings.manage")),
):
    setting = await AdminService.update_setting(db, key, data.value, actor=current_user)
    if not setting:
        raise HTTPException(status_code=404, detail="System setting not found")
    return setting


# ============================================================
# 16. RBAC MANAGEMENT
# ============================================================
@router.get(
    "/rbac/roles",
    response_model=list[AdminRoleItem],
    summary="List RBAC roles and permissions",
)
async def get_rbac_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.view")),
):
    return await AdminService.list_roles(db)


@router.put(
    "/rbac/roles/{name}",
    response_model=AdminRoleItem,
    summary="Update permissions for an administrative role",
)
async def update_rbac_role(
    name: str,
    data: UpdateRolePermissionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage")),
):
    try:
        role = await AdminService.update_role_permissions(
            db, name, data.permissions, actor=current_user
        )
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/rbac/assign",
    summary="Assign role to a user",
)
async def assign_user_role(
    data: AssignUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("rbac.manage")),
):
    try:
        success = await AdminService.update_user_role(
            db, data.user_id, role=data.role, actor=current_user
        )
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "Role assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 17. RAG, LEARNING, CONTESTS
# ============================================================
@router.get(
    "/rag/status",
    response_model=RAGStatusResponse,
    summary="Inspect RAG question vector indexing health",
)
async def get_rag_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("rag.view")),
):
    return await AdminService.get_rag_status(db)


@router.get(
    "/learning/stats",
    response_model=LearningStatsResponse,
    summary="Inspect learning intelligence analytics",
)
async def get_learning_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analytics.view")),
):
    return await AdminService.get_learning_stats(db)


@router.get(
    "/contests",
    summary="List competitive coding contests for admin inspection",
)
async def get_contests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.view")),
):
    query = select(Contest).order_by(desc(Contest.created_at))
    total_res = await db.execute(select(func.count(Contest.id)))
    total = total_res.scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = (await db.execute(query)).scalars().all()
    contests = [
        {
            "id": c.id,
            "title": c.title,
            "slug": c.slug,
            "status": c.status,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "duration_minutes": c.duration_minutes,
            "participant_count": getattr(c, "max_participants", 0) or 0,
            "is_featured": getattr(c, "is_featured", False),
        }
        for c in rows
    ]
    return {"contests": contests, "total": total, "page": page, "page_size": page_size}


@router.post(
    "/contests",
    summary="Create competitive coding contest",
)
async def create_contest(
    data: CreateContestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.manage")),
):
    contest = await AdminService.create_contest(db, data, actor=current_user)
    return contest


@router.get(
    "/contests/{contest_id}",
    summary="Get contest details for admin",
)
async def get_contest_detail_admin(
    contest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.view")),
):
    res = await db.execute(select(Contest).where(Contest.id == contest_id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contest not found")
    return c


@router.put(
    "/contests/{contest_id}",
    summary="Update contest details and schedule",
)
async def update_contest(
    contest_id: uuid.UUID,
    data: UpdateContestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.manage")),
):
    contest = await AdminService.update_contest(db, contest_id, data, actor=current_user)
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return contest


@router.delete(
    "/contests/{contest_id}",
    summary="Archive/Delete contest",
)
async def delete_contest(
    contest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.manage")),
):
    success = await AdminService.delete_contest(db, contest_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Contest not found")
    return {"message": "Contest archived successfully"}


@router.post(
    "/contests/{contest_id}/problems",
    summary="Add coding problem to contest",
)
async def add_contest_problem(
    contest_id: uuid.UUID,
    data: AddContestProblemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.manage")),
):
    cp = await AdminService.add_contest_problem(db, contest_id, data, actor=current_user)
    return cp


@router.delete(
    "/contests/{contest_id}/problems/{problem_id}",
    summary="Remove coding problem from contest",
)
async def remove_contest_problem(
    contest_id: uuid.UUID,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.manage")),
):
    success = await AdminService.remove_contest_problem(db, contest_id, problem_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Contest problem link not found")
    return {"message": "Problem removed from contest successfully"}


@router.get(
    "/contests/{contest_id}/registrations",
    summary="View contest registrations list",
)
async def get_contest_registrations(
    contest_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("contests.view")),
):
    return await AdminService.get_contest_registrations(db, contest_id, page=page, page_size=page_size)


# ============================================================
# 18. CODING PROBLEMS MANAGEMENT (FEATURE 07)
# ============================================================
@router.post(
    "/coding/problems",
    summary="Create coding problem with test cases and editorial",
)
async def create_coding_problem(
    data: CreateCodingProblemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coding.manage")),
):
    prob = await AdminService.create_coding_problem(db, data, actor=current_user)
    return prob


@router.put(
    "/coding/problems/{problem_id}",
    summary="Update coding problem specifications",
)
async def update_coding_problem(
    problem_id: uuid.UUID,
    data: UpdateCodingProblemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coding.manage")),
):
    prob = await AdminService.update_coding_problem(db, problem_id, data, actor=current_user)
    if not prob:
        raise HTTPException(status_code=404, detail="Coding problem not found")
    return prob


@router.delete(
    "/coding/problems/{problem_id}",
    summary="Archive coding problem",
)
async def delete_coding_problem(
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("coding.manage")),
):
    success = await AdminService.delete_coding_problem(db, problem_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Coding problem not found")
    return {"message": "Coding problem archived successfully"}


# ============================================================
# 19. PRACTICE SETS / MOCK TESTS MANAGEMENT (FEATURE 08)
# ============================================================
@router.get(
    "/practice-sets",
    summary="List practice sets",
)
async def list_practice_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    topic: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    return await AdminService.list_practice_sets(
        db, page=page, page_size=page_size, topic=topic, difficulty=difficulty, search=search
    )


@router.post(
    "/practice-sets",
    summary="Create practice set",
)
async def create_practice_set(
    data: CreatePracticeSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    ps = await AdminService.create_practice_set(db, data, actor=current_user)
    return ps


@router.get(
    "/practice-sets/{set_id}",
    summary="Get practice set details",
)
async def get_practice_set(
    set_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    ps = await AdminService.get_practice_set(db, set_id)
    if not ps:
        raise HTTPException(status_code=404, detail="Practice set not found")
    return ps


@router.put(
    "/practice-sets/{set_id}",
    summary="Update practice set",
)
async def update_practice_set(
    set_id: uuid.UUID,
    data: UpdatePracticeSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    ps = await AdminService.update_practice_set(db, set_id, data, actor=current_user)
    if not ps:
        raise HTTPException(status_code=404, detail="Practice set not found")
    return ps


@router.delete(
    "/practice-sets/{set_id}",
    summary="Archive practice set",
)
async def delete_practice_set(
    set_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    success = await AdminService.delete_practice_set(db, set_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Practice set not found")
    return {"message": "Practice set archived successfully"}


@router.post(
    "/practice-sets/{set_id}/questions",
    summary="Add question to practice set",
)
async def add_practice_set_question(
    set_id: uuid.UUID,
    data: AddPracticeSetQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    psq = await AdminService.add_practice_set_question(db, set_id, data, actor=current_user)
    return psq


@router.delete(
    "/practice-sets/{set_id}/questions/{question_id}",
    summary="Remove question from practice set",
)
async def remove_practice_set_question(
    set_id: uuid.UUID,
    question_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("practice_sets.manage")),
):
    success = await AdminService.remove_practice_set_question(db, set_id, question_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Question link not found in practice set")
    return {"message": "Question removed from practice set"}


# ============================================================
# 20. INTERVIEW CONFIGURATIONS / TEMPLATES (FEATURE 03)
# ============================================================
@router.get(
    "/interview-configs",
    summary="List AI interview configurations/templates",
)
async def list_interview_configs(
    category: str | None = None,
    difficulty: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.manage")),
):
    return await AdminService.list_interview_configs(db, category=category, difficulty=difficulty)


@router.post(
    "/interview-configs",
    summary="Create AI interview configuration",
)
async def create_interview_config(
    data: CreateInterviewConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.manage")),
):
    cfg = await AdminService.create_interview_config(db, data, actor=current_user)
    return cfg


@router.get(
    "/interview-configs/{config_id}",
    summary="Get AI interview configuration detail",
)
async def get_interview_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.manage")),
):
    cfg = await AdminService.get_interview_config(db, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Interview configuration not found")
    return cfg


@router.put(
    "/interview-configs/{config_id}",
    summary="Update AI interview configuration",
)
async def update_interview_config(
    config_id: uuid.UUID,
    data: UpdateInterviewConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.manage")),
):
    cfg = await AdminService.update_interview_config(db, config_id, data, actor=current_user)
    if not cfg:
        raise HTTPException(status_code=404, detail="Interview configuration not found")
    return cfg


@router.delete(
    "/interview-configs/{config_id}",
    summary="Archive AI interview configuration",
)
async def delete_interview_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("interviews.manage")),
):
    success = await AdminService.delete_interview_config(db, config_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Interview configuration not found")
    return {"message": "Interview configuration archived successfully"}


# ============================================================
# 21. CAREER ROADMAPS (FEATURE 05)
# ============================================================
@router.get(
    "/roadmaps",
    summary="List career roadmaps",
)
async def list_career_roadmaps(
    target_role: str | None = None,
    difficulty: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roadmaps.manage")),
):
    return await AdminService.list_career_roadmaps(db, target_role=target_role, difficulty=difficulty)


@router.post(
    "/roadmaps",
    summary="Create career roadmap",
)
async def create_career_roadmap(
    data: CreateCareerRoadmapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roadmaps.manage")),
):
    crm = await AdminService.create_career_roadmap(db, data, actor=current_user)
    return crm


@router.get(
    "/roadmaps/{roadmap_id}",
    summary="Get career roadmap detail",
)
async def get_career_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roadmaps.manage")),
):
    crm = await AdminService.get_career_roadmap(db, roadmap_id)
    if not crm:
        raise HTTPException(status_code=404, detail="Career roadmap not found")
    return crm


@router.put(
    "/roadmaps/{roadmap_id}",
    summary="Update career roadmap",
)
async def update_career_roadmap(
    roadmap_id: uuid.UUID,
    data: UpdateCareerRoadmapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roadmaps.manage")),
):
    crm = await AdminService.update_career_roadmap(db, roadmap_id, data, actor=current_user)
    if not crm:
        raise HTTPException(status_code=404, detail="Career roadmap not found")
    return crm


@router.delete(
    "/roadmaps/{roadmap_id}",
    summary="Archive career roadmap",
)
async def delete_career_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("roadmaps.manage")),
):
    success = await AdminService.delete_career_roadmap(db, roadmap_id, actor=current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Career roadmap not found")
    return {"message": "Career roadmap archived successfully"}


# ============================================================
# 22. CANDIDATE 360 VIEW (FEATURE 14)
# ============================================================
@router.get(
    "/candidates/{candidate_id}/360",
    response_model=Candidate360Response,
    summary="Get comprehensive candidate 360 profile without secrets",
)
async def get_candidate_360(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    c360 = await AdminService.get_candidate_360(db, candidate_id)
    if not c360:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c360


# ============================================================
# 23. CANDIDATE DASHBOARD CONFIGURATION (FEATURE 16)
# ============================================================
@router.get(
    "/dashboard-config",
    summary="Get candidate dashboard module visibility configuration",
)
async def get_dashboard_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    return await AdminService.get_dashboard_config(db)


@router.put(
    "/dashboard-config",
    summary="Update candidate dashboard module visibility configuration",
)
async def update_dashboard_config(
    data: DashboardConfigSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings.manage")),
):
    return await AdminService.update_dashboard_config(db, data.model_dump(), actor=current_user)


# ============================================================
# 24. FEATURED CONTENT INSPECTION (FEATURE 15)
# ============================================================
@router.get(
    "/featured-content",
    summary="Get currently active featured items across all platforms",
)
async def get_featured_content_admin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    return await AdminService.get_featured_content(db)

