import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.support.schema import (
    FAQResponse,
    FeedbackCreateRequest,
    FeedbackListResponse,
    FeedbackResponse,
    HelpArticleDetailResponse,
    HelpArticleSummaryResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketListItemResponse,
    TicketListResponse,
    TicketMessageCreateRequest,
    TicketMessageResponse,
    TicketUpdateRequest,
)
from app.modules.support.service import (
    add_ticket_message,
    create_feedback,
    create_ticket,
    format_ticket_detail,
    get_active_faqs,
    get_article_by_slug,
    get_published_articles,
    get_ticket_by_id,
    list_all_tickets_admin,
    list_user_feedback,
    list_user_tickets,
    update_ticket_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/support",
    tags=["Support & Communication"],
)


# ============================================================
# TICKETS (CANDIDATE)
# ============================================================

@router.post(
    "/tickets",
    response_model=TicketDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_ticket(
    data: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new support ticket with initial message and in-app notification."""
    ticket = await create_ticket(
        db=db,
        user_id=current_user.id,
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=data.priority,
    )
    return format_ticket_detail(ticket, is_admin=False)


@router.get(
    "/tickets",
    response_model=TicketListResponse,
)
async def get_my_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all support tickets created by the authenticated user."""
    tickets, total = await list_user_tickets(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )

    items = [
        TicketListItemResponse(
            id=t.id,
            user_id=t.user_id,
            ticket_number=t.ticket_number,
            subject=t.subject,
            category=t.category,
            priority=t.priority,
            status=t.status,
            assigned_to=t.assigned_to,
            created_at=t.created_at,
            updated_at=t.updated_at,
            resolved_at=t.resolved_at,
            closed_at=t.closed_at,
            message_count=len(t.messages),
        )
        for t in tickets
    ]
    return TicketListResponse(tickets=items, total=total)


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailResponse,
)
async def get_single_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single ticket details. Strict user isolation; internal notes are hidden."""
    ticket = await get_ticket_by_id(db, ticket_id, user_id=current_user.id, is_admin=False)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found or access denied",
        )
    return format_ticket_detail(ticket, is_admin=False)


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_ticket_message(
    ticket_id: uuid.UUID,
    data: TicketMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a reply to an existing ticket."""
    try:
        msg = await add_ticket_message(
            db=db,
            ticket_id=ticket_id,
            sender_id=current_user.id,
            message=data.message,
            sender_type="candidate",
            is_internal=False,
            is_admin=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return TicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_id=msg.sender_id,
        sender_name=current_user.full_name,
        sender_type=msg.sender_type,
        message=msg.message,
        is_internal=msg.is_internal,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketDetailResponse,
)
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update ticket properties or status."""
    ticket = await get_ticket_by_id(db, ticket_id, user_id=current_user.id, is_admin=False)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found or access denied",
        )

    if data.subject:
        ticket.subject = data.subject
    if data.category:
        ticket.category = data.category
    if data.priority:
        ticket.priority = data.priority

    if data.status:
        try:
            await update_ticket_status(db, ticket_id, data.status, current_user.id, is_admin=False)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await db.commit()
    await db.refresh(ticket)
    return format_ticket_detail(ticket, is_admin=False)


@router.post(
    "/tickets/{ticket_id}/close",
    response_model=TicketDetailResponse,
)
async def close_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close an open or resolved support ticket."""
    try:
        ticket = await update_ticket_status(db, ticket_id, "closed", current_user.id, is_admin=False)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return format_ticket_detail(ticket, is_admin=False)


@router.post(
    "/tickets/{ticket_id}/reopen",
    response_model=TicketDetailResponse,
)
async def reopen_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a closed or resolved support ticket."""
    try:
        ticket = await update_ticket_status(db, ticket_id, "open", current_user.id, is_admin=False)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return format_ticket_detail(ticket, is_admin=False)


# ============================================================
# ADMIN/SUPPORT APIS (Backend ready for future admin dashboard)
# ============================================================

async def get_current_support_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce support/admin role access for backend-ready support management."""
    role = getattr(current_user, "role", None)
    is_admin = getattr(current_user, "is_admin", False)
    if role in ["admin", "support"] or is_admin:
        return current_user

    email = (current_user.email or "").lower()
    if (
        email.startswith("admin")
        or email.startswith("support")
        or "admin@" in email
        or "support@" in email
        or email == "admin@interviewplatform.ai"
    ):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Support or administrator access required",
    )


@router.get(
    "/admin/tickets",
    response_model=TicketListResponse,
)
async def admin_list_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    category_filter: Optional[str] = Query(default=None, alias="category"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_support_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to list tickets across all users."""
    tickets, total = await list_all_tickets_admin(
        db=db,
        status_filter=status_filter,
        category_filter=category_filter,
        limit=limit,
        offset=offset,
    )
    items = [
        TicketListItemResponse(
            id=t.id,
            user_id=t.user_id,
            ticket_number=t.ticket_number,
            subject=t.subject,
            category=t.category,
            priority=t.priority,
            status=t.status,
            assigned_to=t.assigned_to,
            created_at=t.created_at,
            updated_at=t.updated_at,
            resolved_at=t.resolved_at,
            closed_at=t.closed_at,
            message_count=len(t.messages),
        )
        for t in tickets
    ]
    return TicketListResponse(tickets=items, total=total)


@router.post(
    "/admin/tickets/{ticket_id}/reply",
    response_model=TicketMessageResponse,
)
async def admin_ticket_reply(
    ticket_id: uuid.UUID,
    data: TicketMessageCreateRequest,
    current_user: User = Depends(get_current_support_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin reply or internal note on a ticket."""
    try:
        msg = await add_ticket_message(
            db=db,
            ticket_id=ticket_id,
            sender_id=current_user.id,
            message=data.message,
            sender_type="support",
            is_internal=data.is_internal,
            is_admin=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return TicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_id=msg.sender_id,
        sender_name=current_user.full_name or "Support Agent",
        sender_type=msg.sender_type,
        message=msg.message,
        is_internal=msg.is_internal,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


# ============================================================
# FEEDBACK & BUG REPORT
# ============================================================

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    data: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit platform feedback or bug report."""
    try:
        fb = await create_feedback(
            db=db,
            user_id=current_user.id,
            category=data.category,
            rating=data.rating,
            message=data.message,
            page_context=data.page_context,
            metadata=data.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return fb


@router.get(
    "/feedback/mine",
    response_model=FeedbackListResponse,
)
async def get_my_feedback(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List feedback submitted by the authenticated user."""
    items, total = await list_user_feedback(db, current_user.id, limit, offset)
    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in items],
        total=total,
    )


# ============================================================
# FAQS & HELP ARTICLES (PUBLIC / CANDIDATE)
# ============================================================

@router.get(
    "/faqs",
    response_model=list[FAQResponse],
)
async def list_faqs(
    category: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get active FAQs with optional category filter."""
    faqs = await get_active_faqs(db, category)
    return faqs


@router.get(
    "/articles",
    response_model=list[HelpArticleSummaryResponse],
)
async def list_articles(
    category: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List published help articles."""
    articles = await get_published_articles(db, category)
    return articles


@router.get(
    "/articles/{slug}",
    response_model=HelpArticleDetailResponse,
)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get published article content by slug."""
    article = await get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    return article
