import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.service import NotificationService
from app.modules.support.model import (
    FAQ,
    Feedback,
    HelpArticle,
    SupportTicket,
    SupportTicketMessage,
)
from app.modules.support.schema import (
    TicketCategory,
    TicketDetailResponse,
    TicketListItemResponse,
    TicketMessageResponse,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# TICKET NUMBER GENERATOR
# ============================================================

async def generate_ticket_number(db: AsyncSession) -> str:
    """Generate sequential ticket number: SUP-YYYYMM-000001"""
    now = utc_now()
    prefix = f"SUP-{now.strftime('%Y%m')}"

    # Count existing tickets with this month's prefix
    stmt = select(func.count(SupportTicket.id)).where(
        SupportTicket.ticket_number.like(f"{prefix}-%")
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    seq = count + 1

    return f"{prefix}-{seq:06d}"


# ============================================================
# TICKET CRUD & MESSAGES
# ============================================================

async def create_ticket(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject: str,
    description: str,
    category: str = "Technical Issue",
    priority: str = "medium",
) -> SupportTicket:
    """Create a new support ticket and its initial message."""
    ticket_num = await generate_ticket_number(db)

    ticket = SupportTicket(
        user_id=user_id,
        ticket_number=ticket_num,
        subject=subject,
        description=description,
        category=category,
        priority=priority.lower(),
        status="open",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(ticket)
    await db.flush()

    # Initial message
    initial_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_id=user_id,
        message=description,
        sender_type="candidate",
        is_internal=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(initial_msg)

    # In-app notification for candidate
    await NotificationService.create_notification(
        db=db,
        user_id=user_id,
        type="ticket_created",
        title="Support Ticket Created",
        message=f"Your ticket #{ticket_num} has been created and assigned to support.",
        icon="🎫",
        event_key=f"ticket_created_{ticket.id}",
        action_url=f"/support/tickets/{ticket.id}",
        commit=False,
    )

    await db.commit()
    await db.refresh(ticket)

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        ticket_payload = {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
        await publish_event(WebSocketEventType.SUPPORT_TICKET_CREATED.value, ticket_payload, user_id=user_id)
        await publish_event(WebSocketEventType.SUPPORT_TICKET_CREATED.value, ticket_payload, role="admin")
    except Exception as ws_err:
        logger.warning("Failed to publish support ticket created event: %s", ws_err)

    return ticket


async def get_ticket_by_id(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    is_admin: bool = False,
) -> SupportTicket | None:
    """Retrieve ticket by ID enforcing user isolation.
    Hides internal notes from candidate view."""
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if not is_admin and user_id is not None:
        stmt = stmt.where(SupportTicket.user_id == user_id)

    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    return ticket


async def list_user_tickets(
    db: AsyncSession,
    user_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SupportTicket], int]:
    """Return paginated list of tickets for a specific user."""
    base_query = select(SupportTicket).where(SupportTicket.user_id == user_id)
    count_query = select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user_id)

    if status_filter:
        base_query = base_query.where(SupportTicket.status == status_filter)
        count_query = count_query.where(SupportTicket.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0

    base_query = base_query.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(base_query)
    tickets = list(result.scalars().all())

    return tickets, total


async def list_all_tickets_admin(
    db: AsyncSession,
    status_filter: str | None = None,
    category_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SupportTicket], int]:
    """Admin-only endpoint to view tickets across all users."""
    base_query = select(SupportTicket)
    count_query = select(func.count(SupportTicket.id))

    if status_filter:
        base_query = base_query.where(SupportTicket.status == status_filter)
        count_query = count_query.where(SupportTicket.status == status_filter)

    if category_filter:
        base_query = base_query.where(SupportTicket.category == category_filter)
        count_query = count_query.where(SupportTicket.category == category_filter)

    total = (await db.execute(count_query)).scalar() or 0

    base_query = base_query.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(base_query)
    tickets = list(result.scalars().all())

    return tickets, total


async def add_ticket_message(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    sender_id: uuid.UUID,
    message: str,
    sender_type: str = "candidate",
    is_internal: bool = False,
    is_admin: bool = False,
) -> SupportTicketMessage:
    """Add a message to a ticket and trigger notification."""
    ticket = await get_ticket_by_id(db, ticket_id, sender_id if not is_admin else None, is_admin=is_admin)
    if not ticket:
        raise ValueError("Ticket not found or unauthorized")

    # Candidate cannot create internal notes
    if not is_admin:
        is_internal = False
        sender_type = "candidate"

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_id=sender_id,
        message=message,
        sender_type=sender_type,
        is_internal=is_internal,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(msg)

    # Update ticket status & timestamps
    ticket.updated_at = utc_now()

    if sender_type in ["support", "admin"] and not is_internal:
        ticket.status = "waiting_for_user"
        # Notify candidate
        await NotificationService.create_notification(
            db=db,
            user_id=ticket.user_id,
            type="ticket_reply",
            title="Support Replied to Your Ticket",
            message=f"New reply on ticket #{ticket.ticket_number}: {message[:80]}...",
            icon="💬",
            event_key=f"ticket_reply_{msg.id}",
            action_url=f"/support/tickets/{ticket.id}",
            commit=False,
        )
    elif sender_type == "candidate":
        # If previously closed or waiting, move to in_progress
        if ticket.status in ["closed", "resolved", "waiting_for_user"]:
            ticket.status = "in_progress"

    await db.commit()
    await db.refresh(msg)

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        msg_payload = {
            "id": str(msg.id),
            "ticket_id": str(ticket.id),
            "sender_id": str(sender_id),
            "sender_type": msg.sender_type,
            "message": msg.message,
            "is_internal": msg.is_internal,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "ticket_status": ticket.status,
        }
        # Admin always gets all ticket messages
        await publish_event(WebSocketEventType.SUPPORT_TICKET_MESSAGE.value, msg_payload, role="admin")
        # Candidates NEVER get internal notes
        if not msg.is_internal:
            await publish_event(WebSocketEventType.SUPPORT_TICKET_MESSAGE.value, msg_payload, user_id=ticket.user_id)
    except Exception as ws_err:
        logger.warning("Failed to publish support ticket message event: %s", ws_err)

    return msg


async def update_ticket_status(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    new_status: str,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> SupportTicket:
    """Update ticket status.
    Candidates can only close or reopen their own tickets."""
    ticket = await get_ticket_by_id(db, ticket_id, user_id if not is_admin else None, is_admin=is_admin)
    if not ticket:
        raise ValueError("Ticket not found or access denied")

    valid_statuses = ["open", "in_progress", "waiting_for_user", "resolved", "closed"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'")

    # Candidates can only transition to 'closed' or 'open' (reopen)
    if not is_admin and new_status not in ["closed", "open"]:
        raise ValueError("Candidates can only close or reopen tickets")

    ticket.status = new_status
    ticket.updated_at = utc_now()

    if new_status == "resolved":
        ticket.resolved_at = utc_now()
    elif new_status == "closed":
        ticket.closed_at = utc_now()
    elif new_status == "open":
        ticket.closed_at = None
        ticket.resolved_at = None

    # Notification for candidate if updated by support/admin
    if is_admin and ticket.user_id != user_id:
        await NotificationService.create_notification(
            db=db,
            user_id=ticket.user_id,
            type="ticket_status",
            title="Ticket Status Updated",
            message=f"Ticket #{ticket.ticket_number} status has been changed to '{new_status}'.",
            icon="🔄",
            event_key=f"ticket_status_{ticket.id}_{new_status}_{int(utc_now().timestamp())}",
            action_url=f"/support/tickets/{ticket.id}",
            commit=False,
        )

    await db.commit()
    await db.refresh(ticket)

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        status_payload = {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }
        await publish_event(WebSocketEventType.SUPPORT_TICKET_STATUS.value, status_payload, user_id=ticket.user_id)
        await publish_event(WebSocketEventType.SUPPORT_TICKET_STATUS.value, status_payload, role="admin")
    except Exception as ws_err:
        logger.warning("Failed to publish support ticket status event: %s", ws_err)

    return ticket


def format_ticket_detail(ticket: SupportTicket, is_admin: bool = False) -> TicketDetailResponse:
    """Filter internal notes for candidate views."""
    msgs = []
    for m in ticket.messages:
        # Hide internal notes from candidates
        if m.is_internal and not is_admin:
            continue
        sender_name = m.sender.full_name if m.sender else None
        msgs.append(
            TicketMessageResponse(
                id=m.id,
                ticket_id=m.ticket_id,
                sender_id=m.sender_id,
                sender_name=sender_name,
                sender_type=m.sender_type,
                message=m.message,
                is_internal=m.is_internal,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )

    return TicketDetailResponse(
        id=ticket.id,
        user_id=ticket.user_id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        assigned_to=ticket.assigned_to,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        messages=msgs,
    )


# ============================================================
# FEEDBACK & BUG REPORTING
# ============================================================

async def create_feedback(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: str,
    rating: int,
    message: str,
    page_context: str | None = None,
    metadata: dict | None = None,
) -> Feedback:
    """Store candidate feedback or bug report."""
    if not (1 <= rating <= 5):
        raise ValueError("Rating must be an integer between 1 and 5")

    fb = Feedback(
        user_id=user_id,
        category=category.lower(),
        rating=rating,
        message=message,
        page_context=page_context,
        status="new",
        metadata_json=metadata or {},
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def list_user_feedback(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Feedback], int]:
    """List feedback submitted by a specific user."""
    count_stmt = select(func.count(Feedback.id)).where(Feedback.user_id == user_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Feedback)
        .where(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list((await db.execute(stmt)).scalars().all())
    return items, total


# ============================================================
# FAQ & HELP ARTICLES
# ============================================================

async def get_active_faqs(
    db: AsyncSession,
    category: str | None = None,
) -> list[FAQ]:
    """Retrieve active FAQs."""
    stmt = select(FAQ).where(FAQ.is_active.is_(True))
    if category and category.lower() != "all":
        stmt = stmt.where(FAQ.category.ilike(category))
    stmt = stmt.order_by(FAQ.display_order.asc(), FAQ.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_published_articles(
    db: AsyncSession,
    category: str | None = None,
) -> list[HelpArticle]:
    """Retrieve published help articles."""
    stmt = select(HelpArticle).where(HelpArticle.is_published.is_(True))
    if category and category.lower() != "all":
        stmt = stmt.where(HelpArticle.category.ilike(category))
    stmt = stmt.order_by(HelpArticle.display_order.asc(), HelpArticle.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_article_by_slug(
    db: AsyncSession,
    slug: str,
) -> HelpArticle | None:
    """Retrieve a single published article by slug."""
    stmt = select(HelpArticle).where(
        HelpArticle.slug == slug,
        HelpArticle.is_published.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================
# SEED DEFAULT HELP & FAQ DATA
# ============================================================

DEFAULT_FAQS = [
    {
        "question": "How does the AI Mock Interview evaluation work?",
        "answer": "Our system evaluates your responses across multiple dimensions: Technical Accuracy, Communication Clarity, Problem-Solving Structure, and Time Management. Evaluators employ Groq-accelerated LLMs to deliver real-time feedback and an ATS-grade score.",
        "category": "Interview",
        "display_order": 1,
    },
    {
        "question": "How do subscription tiers differ in interview and problem limits?",
        "answer": "The Free plan includes 3 AI interviews/month and 5 coding problems/day. The Pro plan increases this to 15 AI interviews/month and unlimited coding problems. The Premium plan unlocks unlimited interviews, coding problems, weak topic telemetry, and priority support.",
        "category": "Subscription",
        "display_order": 2,
    },
    {
        "question": "Are payments secure and can I cancel anytime?",
        "answer": "Yes. All transactions are processed through Razorpay's PCI-DSS Level 1 certified gateway. We support UPI, Credit/Debit cards, and Netbanking. You can cancel your subscription at any time with a single click from the Subscription settings page.",
        "category": "Payment",
        "display_order": 3,
    },
    {
        "question": "What is the ATS Resume Intelligence score based on?",
        "answer": "Our ATS scanner analyzes keyword alignment, quantifiable achievement metrics, formatting readability, and semantic role-fit to produce a 0–100 score along with specific line-by-line optimization suggestions.",
        "category": "Resume",
        "display_order": 4,
    },
    {
        "question": "How does the Coding Arena run my code?",
        "answer": "Code is executed in isolated, low-latency micro-containers with strict time and memory limits. We test against both public and hidden test cases across Python, JavaScript, Java, and C++.",
        "category": "Coding",
        "display_order": 5,
    },
    {
        "question": "How does the Anti-Cheating system function during interviews?",
        "answer": "The anti-cheating system monitors presence, face visibility, and secondary device activity in the client browser. It ensures integrity for both practice and competitive assessments.",
        "category": "Technical",
        "display_order": 6,
    },
    {
        "question": "How do I update my profile or reset my password?",
        "answer": "Navigate to Settings → Account & Profile. You can update your contact information, education, career target role, and manage password resets securely.",
        "category": "Account",
        "display_order": 7,
    },
]

DEFAULT_ARTICLES = [
    {
        "title": "Mastering Technical Interviews with the AI Platform",
        "slug": "mastering-technical-interviews",
        "category": "Interview",
        "display_order": 1,
        "content": """# Mastering Technical Interviews

Technical interviews require a blend of strong algorithmic foundation, structured communication, and calm execution.

### Key Strategies
1. **Understand Before Coding**: Restate the problem, clarify edge cases, and ask about constraints.
2. **Think Aloud**: Verbalize your thought process so the AI interviewer understands your trade-offs.
3. **Use the STAR Method for Behavioral**: Describe the Situation, Task, Action, and quantifiable Result.

### Recommended Practice Routine
- Complete at least **1 AI mock session per week**.
- Practice 2–3 algorithmic problems daily in the Coding Arena.
- Review your Weak Topic Radar in the Dashboard to target areas with scores below 70%.""",
    },
    {
        "title": "Understanding Your Subscription & Billing",
        "slug": "understanding-subscriptions-and-billing",
        "category": "Subscription",
        "display_order": 2,
        "content": """# Understanding Subscriptions & Billing

We offer transparent, non-recurring subscription tiers tailored to your preparation timeline.

### Plan Breakdown
- **Free**: 3 AI Interviews/mo, 5 Coding Problems/day, 2 Resume Scans/mo.
- **Pro (₹499/mo)**: 15 AI Interviews/mo, Unlimited Coding, 10 Resume Scans/mo, Advanced Analytics.
- **Premium (₹999/mo)**: Unlimited Interviews, Priority Support, Dedicated Career Pathing.

### Invoices & Tax
Every payment generates an official GST tax invoice with an idempotency key (INV-YYYYMM-XXXXXX). You can view and download invoices anytime from the Billing tab.""",
    },
    {
        "title": "Optimizing Your Resume for Applicant Tracking Systems",
        "slug": "optimizing-resume-for-ats",
        "category": "Resume",
        "display_order": 3,
        "content": """# Optimizing Your Resume for ATS

Applicant Tracking Systems parse candidate resumes before a recruiter ever reviews them.

### Tips for Higher ATS Match Rates
- **Use Standard Section Headers**: Work Experience, Education, Technical Skills, Projects.
- **Incorporate Targeted Keywords**: Mirror phrasing from your target job description.
- **Quantify Impact**: e.g., 'Reduced API latency by 42% by introducing Redis caching'.
- **Avoid Heavy Graphics**: Tables and multi-column designs can confuse text extractors.""",
    },
]


async def seed_support_content(db: AsyncSession) -> None:
    """Seed default FAQs and Help Articles if not already in database."""
    # Seed FAQs
    for f in DEFAULT_FAQS:
        stmt = select(FAQ).where(FAQ.question == f["question"])
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            db.add(FAQ(**f))

    # Seed Articles
    for a in DEFAULT_ARTICLES:
        stmt = select(HelpArticle).where(HelpArticle.slug == a["slug"])
        exists = (await db.execute(stmt)).scalar_one_or_none()
        if not exists:
            db.add(HelpArticle(**a))

    await db.commit()
