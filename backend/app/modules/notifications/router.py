import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.notifications.schema import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.modules.notifications.service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
)
async def get_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    category: str | None = Query(default=None),
    type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated, filtered notification list for the authenticated user.
    """
    # Ensure any real platform achievements, interviews, or practice milestones are synced
    await NotificationService.sync_platform_events(db, current_user.id)

    return await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        unread_only=unread_only,
        category=category,
        type_filter=type,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get unread notification count for the authenticated user.
    """
    count = await NotificationService.get_unread_count(db, current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a specific notification as read, enforcing strict user ownership.
    """
    notif = await NotificationService.mark_as_read(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return MarkReadResponse(
        message="Notification marked as read",
        id=str(notif.id),
        is_read=True,
    )


@router.patch(
    "/read-all",
    response_model=MarkAllReadResponse,
)
@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all unread notifications for the current user as read.
    """
    updated_count = await NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id,
    )
    return MarkAllReadResponse(
        message="All notifications marked as read",
        updated_count=updated_count,
    )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific notification, enforcing strict user ownership.
    """
    deleted = await NotificationService.delete_notification(
        db=db,
        user_id=current_user.id,
        notification_id=notification_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"message": "Notification deleted successfully"}
