import logging
import uuid

from fastapi import WebSocket, status
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.modules.auth.model import User

logger = logging.getLogger(__name__)


class AuthenticatedWSUser:
    def __init__(self, user_id: uuid.UUID, email: str, role: str = "candidate"):
        self.id = user_id
        self.email = email
        self.role = role


async def authenticate_websocket(websocket: WebSocket) -> AuthenticatedWSUser | None:
    """
    Authenticates a WebSocket connection using the JWT access token.
    Sources checked:
      1. Query param: `?token=<jwt>`
      2. Sec-WebSocket-Protocol or Authorization header
    Validates token signature, expiration, user existence in DB, and account active status.
    Strictly derives user identity from JWT payload `sub`.
    """
    token: str | None = websocket.query_params.get("token")

    if not token:
        # Check Authorization header if present
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        # Check subprotocols
        subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        for proto in subprotocols:
            proto_clean = proto.strip()
            if proto_clean and not proto_clean.startswith("vite"):
                token = proto_clean
                break

    if not token:
        logger.warning("WebSocket auth rejected: No token provided")
        return None

    # Decode and verify token cryptographic signature and expiration
    raw_sub = decode_access_token(token)
    if not raw_sub:
        logger.warning("WebSocket auth rejected: Invalid or expired token")
        return None

    try:
        user_uuid = uuid.UUID(raw_sub)
    except (ValueError, TypeError):
        logger.warning("WebSocket auth rejected: Invalid sub in token (%s)", raw_sub)
        return None

    # Verify user exists in database and account is active
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_uuid)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                logger.warning("WebSocket auth rejected: User %s not found or inactive", user_uuid)
                return None

            # Determine role (support admin or standard candidate)
            role = "candidate"
            if getattr(user, "is_admin", False) or "admin" in user.email.lower() or "support" in user.email.lower():
                role = "admin"

            return AuthenticatedWSUser(
                user_id=user.id,
                email=user.email,
                role=role,
            )
    except Exception as e:
        logger.error("WebSocket auth database error: %s", e)
        return None
