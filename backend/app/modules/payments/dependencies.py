"""Subscription limit & entitlement dependencies for FastAPI routes."""
import logging
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.payments.service import check_quota

logger = logging.getLogger(__name__)


def require_quota(action: str) -> Callable:
    """Dependency factory that verifies user hasn't exceeded plan limits for `action`."""
    async def _quota_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        allowed, reason = await check_quota(db, current_user.id, action)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "subscription_limit_exceeded",
                    "action": action,
                    "message": reason,
                    "upgrade_url": "/subscription",
                },
            )

    return _quota_checker
