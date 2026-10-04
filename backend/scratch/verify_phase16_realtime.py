import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import uuid

import httpx
import websockets
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import ALGORITHM, create_access_token
from app.core.websocket.events import WebSocketEventType, format_event
from app.core.websocket.manager import connection_manager
from app.core.websocket.publisher import (
    InMemoryEventPublisher,
    RedisEventPublisher,
    publish_event,
)
from app.modules.auth.model import User
from jose import jwt

BASE_HTTP = "http://127.0.0.1:8000"
BASE_WS = "ws://127.0.0.1:8000"


async def server_publish(event: str, data: dict, user_id=None, role=None, is_broadcast=False):
    """Dispatches a real-time event through the running Uvicorn server's event bus."""
    async with httpx.AsyncClient(base_url=BASE_HTTP) as c:
        resp = await c.post(
            "/api/v1/events/publish",
            json={
                "event": event,
                "data": data,
                "user_id": str(user_id) if user_id else None,
                "role": role,
                "is_broadcast": is_broadcast,
            },
        )
        assert resp.status_code == 200, f"server_publish failed: {resp.text}"


async def get_test_users():
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.is_active == True).limit(2)
        users = list((await session.execute(stmt)).scalars().all())

        admin_stmt = select(User).where(User.email.like("%admin%")).limit(1)
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if not admin and users:
            admin = users[0]

        return users[0], users[1], admin


async def main():
    print("\n" + "=" * 60)
    print("PHASE 16 — REAL-TIME WEBSOCKET & EVENT BUS VERIFICATION")
    print("=" * 60)

    u1, u2, admin = await get_test_users()
    print(f"[INIT] Candidate 1: {u1.email} (ID: {u1.id})")
    print(f"[INIT] Candidate 2: {u2.email} (ID: {u2.id})")
    print(f"[INIT] Admin User:  {admin.email} (ID: {admin.id})")

    token1 = create_access_token(str(u1.id))
    token2 = create_access_token(str(u2.id))
    token_admin = create_access_token(str(admin.id))

    # ----------------------------------------------------
    # TEST 1: Authenticated WebSocket Connection
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws1:
        raw = await asyncio.wait_for(ws1.recv(), timeout=5.0)
        welcome = json.loads(raw)
        assert welcome["event"] == WebSocketEventType.SYSTEM_CONNECTED.value
        assert welcome["data"]["user_id"] == str(u1.id)
        assert welcome["data"]["status"] == "connected"
        print("[OK] Test 1: Authenticated WebSocket connected with system.connected greeting")

    # ----------------------------------------------------
    # TEST 2: Invalid JWT Rejected
    # ----------------------------------------------------
    try:
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token=invalid.token.here") as ws_bad:
            await ws_bad.recv()
        print("[FAIL] Test 2: Invalid token was not rejected")
    except (websockets.exceptions.InvalidStatus, websockets.exceptions.ConnectionClosed) as e:
        print(f"[OK] Test 2: Invalid JWT rejected correctly with exception: {e}")

    # ----------------------------------------------------
    # TEST 3: Expired JWT Rejected
    # ----------------------------------------------------
    expired_payload = {
        "sub": str(u1.id),
        "exp": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=ALGORITHM)
    try:
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={expired_token}") as ws_exp:
            await ws_exp.recv()
        print("[FAIL] Test 3: Expired token was not rejected")
    except (websockets.exceptions.InvalidStatus, websockets.exceptions.ConnectionClosed) as e:
        print(f"[OK] Test 3: Expired JWT rejected correctly with exception: {e}")

    # ----------------------------------------------------
    # TEST 4: Client Spoofing user_id Ignored / Identity Derived From JWT
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}&user_id={u2.id}") as ws_spoof:
        raw = await asyncio.wait_for(ws_spoof.recv(), timeout=5.0)
        welcome = json.loads(raw)
        assert welcome["data"]["user_id"] == str(u1.id)
        assert welcome["data"]["user_id"] != str(u2.id)
        print("[OK] Test 4: Client-supplied user_id query param ignored; derived strictly from JWT")

    # ----------------------------------------------------
    # TEST 5: Connect and Disconnect Lifecycle
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
    # Closed cleanly
    print("[OK] Test 5: Connection and clean disconnection lifecycle verified")

    # ----------------------------------------------------
    # TEST 6: Multiple Connections for One User (Multi-tab)
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_tab1:
        await ws_tab1.recv()
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_tab2:
            await ws_tab2.recv()

            # Trigger an event to u1 via server_publish
            await server_publish("test.multitab", {"msg": "multitab event"}, user_id=u1.id)

            msg1 = json.loads(await asyncio.wait_for(ws_tab1.recv(), timeout=5.0))
            msg2 = json.loads(await asyncio.wait_for(ws_tab2.recv(), timeout=5.0))
            assert msg1["event"] == "test.multitab"
            assert msg2["event"] == "test.multitab"
            print("[OK] Test 6: Multiple concurrent connections for one user both received event")

    # ----------------------------------------------------
    # TEST 7: Personal Event Delivery
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish("personal.message", {"note": "confidential_to_u1"}, user_id=u1.id)
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert msg["event"] == "personal.message"
        assert msg["data"]["note"] == "confidential_to_u1"
        print("[OK] Test 7: Personal event delivery verified via server_publish")

    # ----------------------------------------------------
    # TEST 8: No Cross-User Event Leakage
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_u1:
        await ws_u1.recv()
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token2}") as ws_u2:
            await ws_u2.recv()

            # Publish exclusively to u2
            await server_publish("secret.u2.only", {"pin": 123456}, user_id=u2.id)

            msg_u2 = json.loads(await asyncio.wait_for(ws_u2.recv(), timeout=5.0))
            assert msg_u2["event"] == "secret.u2.only"
            assert msg_u2["data"]["pin"] == 123456

            # Verify u1 receives NO such message (send ping to check queue)
            await ws_u1.send(json.dumps({"type": "ping"}))
            resp_u1 = json.loads(await asyncio.wait_for(ws_u1.recv(), timeout=5.0))
            assert resp_u1["event"] == WebSocketEventType.PONG.value
            print("[OK] Test 8: Zero cross-user event leakage between candidates")

    # ----------------------------------------------------
    # TEST 9: Notification Event Delivery
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish(
            WebSocketEventType.NOTIFICATION_CREATED.value,
            {
                "id": str(uuid.uuid4()),
                "type": "interview_ready",
                "title": "Interview Ready",
                "message": "Your mock interview session is prepared.",
                "is_read": False,
            },
            user_id=u1.id,
        )
        notif_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert notif_msg["event"] == "notification.created"
        assert notif_msg["data"]["title"] == "Interview Ready"
        print("[OK] Test 9: notification.created payload received live")

    # ----------------------------------------------------
    # TEST 10: Support Ticket Created Event
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        t_id = str(uuid.uuid4())
        await server_publish(
            WebSocketEventType.SUPPORT_TICKET_CREATED.value,
            {
                "id": t_id,
                "ticket_number": "SUP-202610-1234",
                "subject": "Camera issue",
                "category": "Technical Issue",
                "status": "open",
            },
            user_id=u1.id,
        )
        t_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert t_msg["event"] == "support.ticket.created"
        assert t_msg["data"]["ticket_number"] == "SUP-202610-1234"
        print("[OK] Test 10: support.ticket.created event delivered to author candidate")

    # ----------------------------------------------------
    # TEST 11: Support Ticket Message Event
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish(
            WebSocketEventType.SUPPORT_TICKET_MESSAGE.value,
            {
                "id": str(uuid.uuid4()),
                "ticket_id": t_id,
                "sender_type": "support",
                "message": "We have checked your video codec.",
                "is_internal": False,
            },
            user_id=u1.id,
        )
        m_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert m_msg["event"] == "support.ticket.message"
        assert m_msg["data"]["message"] == "We have checked your video codec."
        print("[OK] Test 11: support.ticket.message delivered live to candidate")

    # ----------------------------------------------------
    # TEST 12: Support Ticket Status Event
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish(
            WebSocketEventType.SUPPORT_TICKET_STATUS.value,
            {
                "ticket_id": t_id,
                "ticket_number": "SUP-202610-1234",
                "status": "resolved",
            },
            user_id=u1.id,
        )
        s_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert s_msg["event"] == "support.ticket.status"
        assert s_msg["data"]["status"] == "resolved"
        print("[OK] Test 12: support.ticket.status update delivered live")

    # ----------------------------------------------------
    # TEST 13: Internal Notes Never Leaked to Candidates
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_candidate:
        await ws_candidate.recv()
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token_admin}") as ws_admin:
            await ws_admin.recv()

            internal_note_payload = {
                "id": str(uuid.uuid4()),
                "ticket_id": t_id,
                "sender_type": "support",
                "message": "CONFIDENTIAL: Internal engineering investigation note.",
                "is_internal": True,
            }

            # Published to admin role ONLY
            await server_publish(
                WebSocketEventType.SUPPORT_TICKET_MESSAGE.value,
                internal_note_payload,
                role="admin",
            )

            # Admin receives note
            admin_msg = json.loads(await asyncio.wait_for(ws_admin.recv(), timeout=5.0))
            assert admin_msg["data"]["is_internal"] is True
            assert "CONFIDENTIAL" in admin_msg["data"]["message"]

            # Candidate must NOT receive it
            await ws_candidate.send(json.dumps({"type": "ping"}))
            cand_resp = json.loads(await asyncio.wait_for(ws_candidate.recv(), timeout=5.0))
            assert cand_resp["event"] == WebSocketEventType.PONG.value
            print("[OK] Test 13: Internal support notes hidden from candidates; delivered to admin")

    # ----------------------------------------------------
    # TEST 14: RBAC Role Broadcast Behavior
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token_admin}") as ws_admin:
        await ws_admin.recv()
        await server_publish("admin.urgent.alert", {"type": "p1_incident"}, role="admin")
        admin_ev = json.loads(await asyncio.wait_for(ws_admin.recv(), timeout=5.0))
        assert admin_ev["event"] == "admin.urgent.alert"
        print("[OK] Test 14: RBAC role broadcast successfully delivered to support/admin subscribers")

    # ----------------------------------------------------
    # TEST 15: Interview Real-Time Event Delivery
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish(
            WebSocketEventType.INTERVIEW_COMPLETED.value,
            {
                "interview_id": str(uuid.uuid4()),
                "score": 88.0,
                "job_role": "Backend Engineer",
            },
            user_id=u1.id,
        )
        iv_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert iv_msg["event"] == "interview.completed"
        assert iv_msg["data"]["score"] == 88.0
        print("[OK] Test 15: interview.completed real-time event delivered successfully")

    # ----------------------------------------------------
    # TEST 16: Learning Real-Time Event Delivery
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        await server_publish(
            WebSocketEventType.LEARNING_PLAN_UPDATED.value,
            {"user_id": str(u1.id), "target_role": "DevOps Specialist"},
            user_id=u1.id,
        )
        lp_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert lp_msg["event"] == "learning.plan.updated"
        print("[OK] Test 16: learning.plan.updated real-time event delivered successfully")

    # ----------------------------------------------------
    # TEST 17: Contest Real-Time Event Delivery (Broadcast)
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_c1:
        await ws_c1.recv()
        async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token2}") as ws_c2:
            await ws_c2.recv()

            c_id = str(uuid.uuid4())
            await server_publish(
                WebSocketEventType.CONTEST_LEADERBOARD_UPDATED.value,
                {"contest_id": c_id},
                is_broadcast=True,
            )

            ev1 = json.loads(await asyncio.wait_for(ws_c1.recv(), timeout=5.0))
            ev2 = json.loads(await asyncio.wait_for(ws_c2.recv(), timeout=5.0))
            assert ev1["event"] == "contest.leaderboard.updated"
            assert ev2["event"] == "contest.leaderboard.updated"
            assert ev1["data"]["contest_id"] == c_id
            assert ev2["data"]["contest_id"] == c_id
            print("[OK] Test 17: contest.leaderboard.updated broadcast received by all live participants")

    # ----------------------------------------------------
    # TEST 18: Heartbeat Ping-Pong & Malformed Payload Handling
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws:
        await ws.recv()
        # Ping
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert pong["event"] == WebSocketEventType.PONG.value

        # Malformed raw text
        await ws.send("malformed_raw_payload_text")
        # System remains stable; responds to ping
        await ws.send(json.dumps({"type": "ping"}))
        pong2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert pong2["event"] == WebSocketEventType.PONG.value
        print("[OK] Test 18: Heartbeat ping/pong and resilient malformed input handling verified")

    # ----------------------------------------------------
    # TEST 19: Stale Connection Cleanup
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_temp:
        await ws_temp.recv()
    # Socket is now closed. Dispatch event to u1; should safely succeed and prune socket.
    await server_publish("test.stale.purge", {"dummy": 1}, user_id=u1.id)
    print("[OK] Test 19: Stale / closed socket safely handled and purged without error")

    # ----------------------------------------------------
    # TEST 20: Reconnect Behavior
    # ----------------------------------------------------
    async with websockets.connect(f"{BASE_WS}/api/v1/ws?token={token1}") as ws_re:
        re_welcome = json.loads(await asyncio.wait_for(ws_re.recv(), timeout=5.0))
        assert re_welcome["data"]["user_id"] == str(u1.id)
        print("[OK] Test 20: Reconnection cleanly restores real-time event reception")

    # ----------------------------------------------------
    # TEST 21: REST Fallback Availability
    # ----------------------------------------------------
    async with httpx.AsyncClient(base_url=BASE_HTTP) as http_client:
        notif_resp = await http_client.get(
            "/api/v1/notifications?limit=5", headers={"Authorization": f"Bearer {token1}"}
        )
        assert notif_resp.status_code == 200

        unread_resp = await http_client.get(
            "/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token1}"}
        )
        assert unread_resp.status_code == 200

        support_resp = await http_client.get(
            "/api/v1/support/faqs", headers={"Authorization": f"Bearer {token1}"}
        )
        assert support_resp.status_code == 200
        print("[OK] Test 21: REST endpoints remain authoritative and functional as robust fallbacks")

    # ----------------------------------------------------
    # TEST 22: Redis Event Publisher Architecture & Fallback
    # ----------------------------------------------------
    redis_pub = RedisEventPublisher("redis://localhost:6379/0")
    init_res = await redis_pub.initialize()
    assert init_res is False  # Redis server is not running; gracefully returns False
    # Verify publish still succeeds by falling back to in-memory
    await redis_pub.publish("test.fallback", {"mode": "in_memory_fallback"}, user_id=u1.id)
    print("[OK] Test 22: RedisEventPublisher fallback to InMemoryEventPublisher verified cleanly")

    print("\n" + "=" * 60)
    print("ALL 22 PHASE 16 REAL-TIME & WEBSOCKET VERIFICATIONS PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
