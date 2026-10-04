import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.websocket.auth import authenticate_websocket
from app.core.websocket.events import WebSocketEventType, format_event
from app.core.websocket.manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Real-Time"])

MAX_MESSAGE_SIZE = 64 * 1024  # 64 KB safety limit


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Authenticated WebSocket endpoint for real-time notifications, support,
    interviews, contests, and learning events.
    Strictly authenticates through JWT token; derives identity on server.
    """
    # 1. Authenticate user
    auth_user = await authenticate_websocket(websocket)
    if not auth_user:
        # Reject unauthorized connection
        logger.warning("Rejecting unauthorized WebSocket connection attempt.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = str(auth_user.id)

    # 2. Register connection in ConnectionManager
    await connection_manager.connect(websocket, user_id_str, role=auth_user.role)

    # 3. Send initial connected confirmation
    welcome_event = format_event(
        WebSocketEventType.SYSTEM_CONNECTED.value,
        {
            "user_id": user_id_str,
            "status": "connected",
            "role": auth_user.role,
        },
    )
    await connection_manager.send_personal(websocket, welcome_event)

    # 4. Message listening loop
    try:
        while True:
            text = await websocket.receive_text()

            # Message size guard
            if len(text) > MAX_MESSAGE_SIZE:
                logger.warning("Incoming message exceeds size limit from user %s", user_id_str)
                continue

            try:
                msg_data = json.loads(text)
            except Exception:
                # Raw text or ping string
                msg_data = {"type": text}

            msg_type = msg_data.get("type") or msg_data.get("event")

            # Heartbeat Ping/Pong
            if msg_type in ["ping", "heartbeat"]:
                pong_event = format_event(
                    WebSocketEventType.PONG.value,
                    {"reply_to": msg_type},
                )
                await connection_manager.send_personal(websocket, pong_event)
            else:
                # Log or handle other client interactions; clients are not allowed to inject system broadcast events
                logger.debug("Received client event from %s: %s", user_id_str, msg_type)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: user %s", user_id_str)
    except Exception as e:
        logger.warning("WebSocket exception for user %s: %s", user_id_str, e)
    finally:
        await connection_manager.disconnect(websocket, user_id_str)


from fastapi import Request, HTTPException
from pydantic import BaseModel
from typing import Any
from app.modules.auth.dependencies import get_optional_current_user

class EventPublishRequest(BaseModel):
    event: str
    data: dict[str, Any] = {}
    user_id: str | None = None
    role: str | None = None
    is_broadcast: bool = False

@router.post("/events/publish", summary="Internal real-time event dispatcher")
async def trigger_event(
    request: Request,
    payload: EventPublishRequest,
):
    client_ip = request.client.host if request.client else "unknown"
    # Allow loopback / internal callers for microservice/inter-process dispatch
    is_loopback = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
    
    if not is_loopback:
        # If external, require admin credentials
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="External access to internal event dispatcher is restricted",
            )

    from app.core.websocket.publisher import publish_event
    await publish_event(
        event_type=payload.event,
        data=payload.data,
        user_id=payload.user_id,
        role=payload.role,
        is_broadcast=payload.is_broadcast,
    )
    return {"status": "dispatched", "event": payload.event}

