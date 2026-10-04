from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# ENUMS
# ============================================================

class TicketCategory(str, Enum):
    ACCOUNT = "Account"
    INTERVIEW = "Interview"
    RESUME = "Resume"
    CODING = "Coding"
    LEARNING = "Learning"
    PAYMENT = "Payment"
    SUBSCRIPTION = "Subscription"
    TECHNICAL_ISSUE = "Technical Issue"
    BUG_REPORT = "Bug Report"
    OTHER = "Other"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ============================================================
# TICKET MESSAGES
# ============================================================

class TicketMessageCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


class TicketMessageResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    sender_id: UUID
    sender_name: str | None = None
    sender_type: str
    message: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# SUPPORT TICKETS
# ============================================================

class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5, max_length=10000)
    category: str = Field(default="Technical Issue")
    priority: str = Field(default="medium")


class TicketUpdateRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=255)
    category: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: UUID | None = None


class TicketListItemResponse(BaseModel):
    id: UUID
    user_id: UUID
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    ticket_number: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    messages: list[TicketMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    tickets: list[TicketListItemResponse]
    total: int


# ============================================================
# FEEDBACK & BUG REPORT
# ============================================================

class FeedbackCreateRequest(BaseModel):
    category: str = Field(default="platform")
    rating: int = Field(ge=1, le=5, default=5)
    message: str = Field(min_length=3, max_length=5000)
    page_context: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: str
    rating: int
    message: str
    page_context: str | None = None
    status: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    items: list[FeedbackResponse]
    total: int


# ============================================================
# FAQ
# ============================================================

class FAQResponse(BaseModel):
    id: UUID
    question: str
    answer: str
    category: str
    display_order: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# HELP ARTICLE
# ============================================================

class HelpArticleSummaryResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    category: str
    content: str = ""
    display_order: int
    is_published: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HelpArticleDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    category: str
    content: str
    display_order: int
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
