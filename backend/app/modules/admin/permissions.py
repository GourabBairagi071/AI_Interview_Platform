from typing import Callable, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

ALL_PERMISSIONS = [
    "users.view",
    "users.manage",
    "interviews.view",
    "interviews.manage",
    "questions.view",
    "questions.create",
    "questions.update",
    "questions.delete",
    "companies.view",
    "companies.manage",
    "resources.view",
    "resources.manage",
    "ai_agents.view",
    "ai_agents.manage",
    "analytics.view",
    "subscriptions.view",
    "subscriptions.manage",
    "payments.view",
    "coupons.manage",
    "invoices.view",
    "support.view",
    "support.manage",
    "feedback.view",
    "feedback.manage",
    "notifications.manage",
    "achievements.manage",
    "audit_logs.view",
    "settings.view",
    "settings.manage",
    "rag.view",
    "rag.manage",
    "contests.view",
    "contests.manage",
    "rbac.view",
    "rbac.manage",
]

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "SUPER_ADMIN": list(ALL_PERMISSIONS),
    "ADMIN": [
        "users.view", "users.manage",
        "interviews.view",
        "questions.view", "questions.create", "questions.update",
        "companies.view", "companies.manage",
        "resources.view", "resources.manage",
        "ai_agents.view",
        "analytics.view",
        "subscriptions.view",
        "payments.view", "coupons.manage", "invoices.view",
        "support.view", "support.manage",
        "feedback.view", "feedback.manage",
        "notifications.manage",
        "achievements.manage",
        "audit_logs.view",
        "settings.view",
        "rag.view",
        "contests.view", "contests.manage",
        "rbac.view",
    ],
    "INTERVIEW_ADMIN": [
        "interviews.view", "interviews.manage",
        "questions.view", "questions.create", "questions.update", "questions.delete",
        "companies.view",
        "ai_agents.view",
        "analytics.view",
        "rag.view",
    ],
    "CONTENT_ADMIN": [
        "questions.view", "questions.create", "questions.update", "questions.delete",
        "companies.view", "companies.manage",
        "resources.view", "resources.manage",
        "rag.view", "rag.manage",
        "contests.view", "contests.manage",
    ],
    "AI_ADMIN": [
        "ai_agents.view", "ai_agents.manage",
        "rag.view", "rag.manage",
        "analytics.view",
        "settings.view",
    ],
    "FINANCE_ADMIN": [
        "subscriptions.view", "subscriptions.manage",
        "payments.view",
        "coupons.manage",
        "invoices.view",
        "analytics.view",
    ],
    "SUPPORT_ADMIN": [
        "support.view", "support.manage",
        "feedback.view", "feedback.manage",
        "users.view",
        "notifications.manage",
    ],
    "ANALYTICS_ADMIN": [
        "analytics.view",
        "audit_logs.view",
        "users.view",
        "interviews.view",
    ],
    "CANDIDATE": [],
}


async def get_effective_permissions(user: User, db: AsyncSession) -> Set[str]:
    """Retrieve the set of effective permissions for a user based on their role."""
    user_role = (user.role or "CANDIDATE").upper()

    # Super admin has unconditional access to all permissions
    if user_role == "SUPER_ADMIN" or user.email.lower() == "admin@interviewplatform.ai":
        return set(ALL_PERMISSIONS)

    # Check database role permissions
    from app.modules.admin.model import AdminRole
    stmt = select(AdminRole).where(AdminRole.name == user_role)
    result = await db.execute(stmt)
    db_role = result.scalar_one_or_none()

    if db_role and db_role.permissions:
        perms = set(db_role.permissions)
        return perms

    # Fallback to default in-code role permissions
    perms = set(DEFAULT_ROLE_PERMISSIONS.get(user_role, []))
    if getattr(user, "is_admin", False) and not perms:
        perms = set(DEFAULT_ROLE_PERMISSIONS.get("ADMIN", []))

    return perms


def require_permission(required_perm: str) -> Callable:
    """FastAPI Dependency for RBAC permission check."""
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_role = (current_user.role or "CANDIDATE").upper()

        # Super admin bypass
        if user_role == "SUPER_ADMIN" or current_user.email.lower() == "admin@interviewplatform.ai":
            return current_user

        perms = await get_effective_permissions(current_user, db)
        if required_perm not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{required_perm}' required",
            )
        return current_user

    return permission_checker
