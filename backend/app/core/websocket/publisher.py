from abc import ABC, abstractmethod
import asyncio
import json
import logging
from typing import Any
import uuid

from app.core.config import settings
from app.core.websocket.events import format_event
from app.core.websocket.manager import connection_manager

logger = logging.getLogger(__name__)

CHANNEL_REALTIME_EVENTS = "interview_platform:realtime_events"


class EventPublisher(ABC):
    """Abstract Event Publisher."""

    @abstractmethod
    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        user_id: str | uuid.UUID | None = None,
        role: str | None = None,
        is_broadcast: bool = False,
        event_id: str | None = None,
    ) -> None:
        pass


class InMemoryEventPublisher(EventPublisher):
    """
    In-process Event Publisher for single-process architectures.
    Directly dispatches events to connected WebSockets via ConnectionManager.
    """

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        user_id: str | uuid.UUID | None = None,
        role: str | None = None,
        is_broadcast: bool = False,
        event_id: str | None = None,
    ) -> None:
        event = format_event(event_type, data, event_id=event_id)

        if is_broadcast:
            await connection_manager.broadcast(event)
        elif user_id is not None:
            await connection_manager.broadcast_to_user(str(user_id), event)
        elif role is not None:
            await connection_manager.broadcast_to_role(role, event)
        else:
            logger.warning("Event %s dropped: No destination user, role, or broadcast flag specified.", event_type)


class RedisEventPublisher(EventPublisher):
    """
    Redis Pub/Sub Event Publisher for multi-process / clustered architectures.
    Publishes events across instances; a background subscriber task listens and delivers to local ConnectionManager.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._in_memory_fallback = InMemoryEventPublisher()
        self._redis_client = None
        self._pubsub_task = None

    async def initialize(self) -> bool:
        try:
            import redis.asyncio as aioredis  # type: ignore

            self._redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            # Verify connectivity
            await self._redis_client.ping()
            # Start background subscriber
            self._pubsub_task = asyncio.create_task(self._listen_redis_channel())
            logger.info("Redis Pub/Sub connected successfully for real-time events.")
            return True
        except Exception as e:
            logger.warning("Redis Pub/Sub unavailable (%s). Falling back to InMemoryEventPublisher.", e)
            self._redis_client = None
            return False

    async def _listen_redis_channel(self) -> None:
        """Background task listening for cross-process messages."""
        try:
            pubsub = self._redis_client.pubsub()
            await pubsub.subscribe(CHANNEL_REALTIME_EVENTS)
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    payload_raw = message.get("data")
                    if payload_raw:
                        envelope = json.loads(payload_raw)
                        target_user = envelope.get("target_user")
                        target_role = envelope.get("target_role")
                        is_bcast = envelope.get("is_broadcast", False)
                        event = envelope.get("event")

                        if is_bcast:
                            await connection_manager.broadcast(event)
                        elif target_user:
                            await connection_manager.broadcast_to_user(target_user, event)
                        elif target_role:
                            await connection_manager.broadcast_to_role(target_role, event)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in Redis Pub/Sub listener: %s", e)

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        user_id: str | uuid.UUID | None = None,
        role: str | None = None,
        is_broadcast: bool = False,
        event_id: str | None = None,
    ) -> None:
        event = format_event(event_type, data, event_id=event_id)

        if not self._redis_client:
            # Fallback to local in-memory
            await self._in_memory_fallback.publish(
                event_type, data, user_id=user_id, role=role, is_broadcast=is_broadcast, event_id=event_id
            )
            return

        payload = {
            "target_user": str(user_id) if user_id is not None else None,
            "target_role": role,
            "is_broadcast": is_broadcast,
            "event": event,
        }

        try:
            await self._redis_client.publish(CHANNEL_REALTIME_EVENTS, json.dumps(payload))
        except Exception as e:
            logger.warning("Failed to publish to Redis Pub/Sub (%s). Falling back to in-memory.", e)
            await self._in_memory_fallback.publish(
                event_type, data, user_id=user_id, role=role, is_broadcast=is_broadcast, event_id=event_id
            )


# Global publisher selection
_active_publisher: EventPublisher = InMemoryEventPublisher()


def get_publisher() -> EventPublisher:
    return _active_publisher


def set_publisher(publisher: EventPublisher) -> None:
    global _active_publisher
    _active_publisher = publisher


async def publish_event(
    event_type: str,
    data: dict[str, Any],
    user_id: str | uuid.UUID | None = None,
    role: str | None = None,
    is_broadcast: bool = False,
    event_id: str | None = None,
) -> None:
    """
    Standard entrypoint for application modules to dispatch real-time events.
    Completely decouples modules from WebSocket internals and Redis topology.
    """
    try:
        publisher = get_publisher()
        await publisher.publish(
            event_type=event_type,
            data=data,
            user_id=user_id,
            role=role,
            is_broadcast=is_broadcast,
            event_id=event_id,
        )
    except Exception as e:
        logger.error("Failed to publish event %s: %s", event_type, e)
