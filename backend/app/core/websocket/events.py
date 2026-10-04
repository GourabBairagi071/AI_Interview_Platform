from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class WebSocketEventType(str, Enum):
    # Notifications
    NOTIFICATION_CREATED = "notification.created"
    NOTIFICATION_READ = "notification.read"

    # Support & Communication
    SUPPORT_TICKET_CREATED = "support.ticket.created"
    SUPPORT_TICKET_MESSAGE = "support.ticket.message"
    SUPPORT_TICKET_STATUS = "support.ticket.status"

    # Interviews
    INTERVIEW_STARTED = "interview.started"
    INTERVIEW_UPDATED = "interview.updated"
    INTERVIEW_COMPLETED = "interview.completed"

    # Learning Intelligence
    LEARNING_PLAN_UPDATED = "learning.plan.updated"

    # Coding & Contests
    CONTEST_STATUS = "contest.status"
    CONTEST_LEADERBOARD_UPDATED = "contest.leaderboard.updated"
    CONTEST_PARTICIPANT_UPDATED = "contest.participant.updated"

    # System & Heartbeat
    SYSTEM_EVENT = "system.event"
    SYSTEM_CONNECTED = "system.connected"
    PING = "ping"
    PONG = "pong"


class EventEnvelope(BaseModel):
    event: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"


def format_event(
    event: str,
    data: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    """Helper to generate standardized event dictionary."""
    return {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "id": event_id or str(uuid.uuid4()),
        "version": "1.0",
    }
