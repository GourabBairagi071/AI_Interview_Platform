from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    ACHIEVEMENT_UNLOCKED = "ACHIEVEMENT_UNLOCKED"
    XP_EARNED = "XP_EARNED"
    LEVEL_UP = "LEVEL_UP"
    STREAK = "STREAK"
    MISSION_COMPLETED = "MISSION_COMPLETED"
    PRACTICE_MILESTONE = "PRACTICE_MILESTONE"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    INTERVIEW_RESULT = "INTERVIEW_RESULT"
    SYSTEM = "SYSTEM"
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_REPLY = "TICKET_REPLY"
    TICKET_STATUS = "TICKET_STATUS"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    SUBSCRIPTION = "SUBSCRIPTION"
    LEARNING_PLAN = "LEARNING_PLAN"


class NotificationCategory(str, Enum):
    ALL = "all"
    UNREAD = "unread"
    ACHIEVEMENTS = "achievements"
    PRACTICE = "practice"
    PROGRESS = "progress"
    INTERVIEWS = "interviews"
    PAYMENT = "payment"
    SUPPORT = "support"
    LEARNING = "learning"
    SYSTEM = "system"


TYPE_TO_CATEGORY = {
    NotificationType.ACHIEVEMENT_UNLOCKED.value: "Achievements",
    NotificationType.XP_EARNED.value: "Practice",
    NotificationType.PRACTICE_MILESTONE.value: "Practice",
    NotificationType.LEVEL_UP.value: "Progress",
    NotificationType.STREAK.value: "Progress",
    NotificationType.MISSION_COMPLETED.value: "Progress",
    NotificationType.INTERVIEW_COMPLETED.value: "Interviews",
    NotificationType.INTERVIEW_RESULT.value: "Interviews",
    NotificationType.SYSTEM.value: "System",
    NotificationType.TICKET_CREATED.value: "Support",
    NotificationType.TICKET_REPLY.value: "Support",
    NotificationType.TICKET_STATUS.value: "Support",
    NotificationType.PAYMENT_SUCCESS.value: "Payment",
    NotificationType.PAYMENT_FAILED.value: "Payment",
    NotificationType.SUBSCRIPTION.value: "Payment",
    NotificationType.LEARNING_PLAN.value: "Learning",
}


CATEGORY_TO_TYPES = {
    "achievements": [NotificationType.ACHIEVEMENT_UNLOCKED.value],
    "practice": [NotificationType.PRACTICE_MILESTONE.value, NotificationType.XP_EARNED.value],
    "progress": [NotificationType.LEVEL_UP.value, NotificationType.STREAK.value, NotificationType.MISSION_COMPLETED.value],
    "interviews": [NotificationType.INTERVIEW_COMPLETED.value, NotificationType.INTERVIEW_RESULT.value],
    "payment": [NotificationType.PAYMENT_SUCCESS.value, NotificationType.PAYMENT_FAILED.value, NotificationType.SUBSCRIPTION.value],
    "support": [NotificationType.TICKET_CREATED.value, NotificationType.TICKET_REPLY.value, NotificationType.TICKET_STATUS.value],
    "learning": [NotificationType.LEARNING_PLAN.value],
    "system": [NotificationType.SYSTEM.value],
}


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    icon: str
    category: str = "System"
    is_read: bool
    created_at: str
    read_at: str | None = None
    action_url: str | None = None
    priority: str = "normal"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem]
    total: int
    page: int
    limit: int
    unread_count: int
    has_next: bool


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    message: str
    id: str
    is_read: bool


class MarkAllReadResponse(BaseModel):
    message: str
    updated_count: int
