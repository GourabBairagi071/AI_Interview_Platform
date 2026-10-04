from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


# ----------------------------------------------------
# Overview & KPIs
# ----------------------------------------------------
class MetricItem(BaseModel):
    label: str
    value: int | float | str
    change: str | None = None
    trend: str | None = None


class ChartDataPoint(BaseModel):
    date: str
    count: int = 0
    value: int | float = 0
    secondary: float | int | None = None


class CategoryCount(BaseModel):
    category: str
    count: int


class DashboardKPIsResponse(BaseModel):
    # Core User KPIs
    total_users: int
    active_users: int
    new_users_30d: int
    new_users: int = 0
    new_users_last_7_days: int = 0

    # Core Interview KPIs
    total_interviews: int
    completed_interviews: int
    avg_interview_score: float | None = None
    average_interview_score: float | None = None

    # ATS Resume Scoring
    avg_ats_score: float | None = None
    average_ats_score: float | None = None

    # Subscription KPIs
    active_subscriptions: int
    total_subscription_plans: int = 0
    active_subscription_users: int = 0
    expired_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    pending_subscriptions: int = 0

    # Payment KPIs
    total_revenue_inr: float
    total_payment_transactions: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    pending_payments: int = 0

    # Support KPIs
    pending_support_tickets: int
    open_support_tickets: int = 0
    total_support_tickets: int = 0
    in_progress_support_tickets: int = 0
    resolved_support_tickets: int = 0
    closed_support_tickets: int = 0

    # Question, Coding, Contest, RAG KPIs
    technical_questions: int = 0
    coding_problems: int = 0
    total_coding_submissions: int = 0
    contests: int = 0
    contest_participants: int = 0
    rag_question_count: int = 0
    rag_indexed_questions: int = 0

    # Charts
    user_growth_chart: list[ChartDataPoint]
    interview_activity_chart: list[ChartDataPoint]
    revenue_chart: list[ChartDataPoint]

    # Categorical distributions
    role_distribution: list[CategoryCount]
    difficulty_distribution: list[CategoryCount]

    # Recent lists
    recent_registrations: list[dict[str, Any]]
    recent_interviews: list[dict[str, Any]]
    recent_payments: list[dict[str, Any]]
    recent_tickets: list[dict[str, Any]]
    recent_activities: list[dict[str, Any]] = Field(default_factory=list)

    # Nested structures for frontend convenience
    kpis: dict[str, Any] = Field(default_factory=dict)
    trends: dict[str, Any] = Field(default_factory=dict)


# ----------------------------------------------------
# User Management
# ----------------------------------------------------
class AdminUserItem(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    interview_count: int = 0
    avg_score: float | None = None
    coding_count: int = 0
    subscription_status: str = "FREE"


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class AdminUserDetailResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: dict[str, Any] | None
    interview_history: list[dict[str, Any]]
    coding_stats: dict[str, Any]
    subscription: dict[str, Any] | None
    support_tickets: list[dict[str, Any]]


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    role: str


# ----------------------------------------------------
# Interview Management
# ----------------------------------------------------
class AdminInterviewItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    user_name: str | None = None
    job_role: str
    difficulty: str
    status: str
    score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AdminInterviewListResponse(BaseModel):
    interviews: list[AdminInterviewItem]
    total: int
    page: int
    page_size: int


class AdminInterviewDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    job_role: str
    difficulty: str
    status: str
    score: float | None = None
    feedback: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    transcript: str | None = None
    question_evaluations: Any | None = None
    questions: Any | None = None
    answers: Any | None = None
    anti_cheating: list[dict[str, Any]] = []
    created_at: datetime
    completed_at: datetime | None = None


# ----------------------------------------------------
# Question Management
# ----------------------------------------------------
class AdminQuestionItem(BaseModel):
    id: str
    technology: str
    technology_slug: str
    topic: str
    topic_slug: str
    subtopic: str
    question: str
    difficulty: str
    question_type: str
    role: str | None = None
    explanation: str | None = None
    source: str
    created_at: datetime


class AdminQuestionListResponse(BaseModel):
    questions: list[AdminQuestionItem]
    total: int
    page: int
    page_size: int


class CreateQuestionRequest(BaseModel):
    id: str | None = None
    technology: str
    topic: str
    subtopic: str = "General"
    question: str
    difficulty: str = "Medium"
    question_type: str = "Technical"
    role: str | None = None
    explanation: str | None = None


class UpdateQuestionRequest(BaseModel):
    technology: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    question: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    role: str | None = None
    explanation: str | None = None


# ----------------------------------------------------
# Company Management
# ----------------------------------------------------
class CompanyItem(BaseModel):
    id: UUID
    name: str
    logo_url: str | None = None
    description: str | None = None
    industry: str
    website: str | None = None
    roles: list[str] = []
    interview_types: list[str] = []
    difficulty: str
    preparation_content: str | None = None
    is_active: bool
    created_at: datetime


class CreateCompanyRequest(BaseModel):
    name: str
    logo_url: str | None = None
    description: str | None = None
    industry: str = "Technology"
    website: str | None = None
    roles: list[str] = []
    interview_types: list[str] = []
    difficulty: str = "Medium"
    preparation_content: str | None = None


class UpdateCompanyRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    roles: list[str] | None = None
    interview_types: list[str] | None = None
    difficulty: str | None = None
    preparation_content: str | None = None
    is_active: bool | None = None


# ----------------------------------------------------
# Learning Resource Management
# ----------------------------------------------------
class LearningResourceItem(BaseModel):
    id: UUID
    title: str
    description: str
    topic: str
    canonical_skill: str
    difficulty: str
    resource_type: str
    url: str | None = None


class CreateResourceRequest(BaseModel):
    title: str
    description: str
    topic: str
    canonical_skill: str
    difficulty: str = "Intermediate"
    resource_type: str = "Documentation"
    url: str | None = None


class UpdateResourceRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    topic: str | None = None
    canonical_skill: str | None = None
    difficulty: str | None = None
    resource_type: str | None = None
    url: str | None = None


# ----------------------------------------------------
# AI Agent Management
# ----------------------------------------------------
class AIAgentConfigItem(BaseModel):
    id: UUID
    agent_key: str
    name: str
    description: str | None = None
    model_identifier: str
    temperature: float
    max_tokens: int
    system_prompt: str | None = None
    is_active: bool
    feature_assignment: str
    updated_at: datetime


class UpdateAIAgentConfigRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    model_identifier: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
    is_active: bool | None = None


# ----------------------------------------------------
# Subscription & Payment Management
# ----------------------------------------------------
class AdminSubscriptionPlanItem(BaseModel):
    id: UUID
    plan_code: str
    name: str
    description: str | None = None
    price_inr: float
    duration_days: int
    interview_limit: int
    resume_analyses_limit: int
    coding_practice_unlimited: bool
    is_active: bool


class CreateSubscriptionPlanRequest(BaseModel):
    plan_code: str
    name: str
    description: str | None = None
    price_inr: float
    duration_days: int = 30
    interview_limit: int = 10
    resume_analyses_limit: int = 5
    coding_practice_unlimited: bool = True
    is_active: bool = True


class AdminPaymentItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    plan_code: str
    amount_inr: float
    currency: str
    status: str
    order_id: str
    payment_id: str | None = None
    created_at: datetime


class AdminCouponItem(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_value: float
    max_discount_inr: float | None = None
    min_order_inr: float = 0.0
    valid_from: datetime
    valid_until: datetime
    usage_limit: int | None = None
    times_used: int
    is_active: bool


class CreateCouponRequest(BaseModel):
    code: str
    discount_type: str  # PERCENTAGE or FLAT
    discount_value: float
    max_discount_inr: float | None = None
    min_order_inr: float = 0.0
    valid_from: datetime
    valid_until: datetime
    usage_limit: int | None = None


class AdminInvoiceItem(BaseModel):
    id: UUID
    invoice_number: str
    user_id: UUID
    user_email: str | None = None
    plan_name: str
    subtotal_inr: float
    tax_inr: float
    discount_inr: float
    total_inr: float
    status: str
    created_at: datetime


# ----------------------------------------------------
# Feedback & Notifications
# ----------------------------------------------------
class AdminFeedbackItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    category: str
    rating: int
    message: str
    page_context: str | None = None
    status: str
    created_at: datetime


class UpdateFeedbackStatusRequest(BaseModel):
    status: str
    resolution_notes: str | None = None


class BroadcastNotificationRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=2)
    type: str = "announcement"  # announcement, maintenance, system_alert, update
    link: str | None = None
    target_role: str | None = None  # None for all, or "CANDIDATE", "ADMIN", etc.


# ----------------------------------------------------
# Achievements
# ----------------------------------------------------
class AdminAchievementItem(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    rarity: str
    xp_reward: int
    target_value: int
    is_active: bool


class CreateAchievementRequest(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    rarity: str = "Common"
    xp_reward: int = 50
    target_value: int = 1
    is_active: bool = True


# ----------------------------------------------------
# Audit Logs & Settings
# ----------------------------------------------------
class AdminAuditLogItem(BaseModel):
    id: UUID
    actor_email: str
    action: str
    resource: str
    resource_id: str | None = None
    details: dict[str, Any]
    ip_address: str | None = None
    created_at: datetime


class SystemSettingItem(BaseModel):
    id: UUID
    key: str
    value: dict[str, Any]
    category: str
    description: str | None = None
    is_sensitive: bool
    updated_by: str | None = None
    updated_at: datetime


class UpdateSystemSettingRequest(BaseModel):
    value: dict[str, Any]


# ----------------------------------------------------
# RBAC
# ----------------------------------------------------
class AdminRoleItem(BaseModel):
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


class UpdateRolePermissionsRequest(BaseModel):
    permissions: list[str]


class AssignUserRoleRequest(BaseModel):
    user_id: UUID
    role: str


# ----------------------------------------------------
# RAG, Learning, Contests
# ----------------------------------------------------
class RAGStatusResponse(BaseModel):
    total_vectors: int
    indexed_questions: int
    categories_count: int
    health_status: str
    sample_topics: list[str]


class LearningStatsResponse(BaseModel):
    total_profiles: int
    avg_readiness_score: float
    total_resources: int
    weak_topics: list[dict[str, Any]]
    popular_skills: list[dict[str, Any]]
