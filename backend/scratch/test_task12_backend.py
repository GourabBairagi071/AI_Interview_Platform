import asyncio
import sys
import uuid
import httpx

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_tests():
    print("=== STARTING TASK 12 NOTIFICATIONS BACKEND VERIFICATION ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create User A
        email_a = f"test_notif_a_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "TestPassword123!"
        resp = await client.post(f"{BASE_URL}/auth/register", json={"email": email_a, "password": pwd, "full_name": "User A"})
        assert resp.status_code == 201, f"User A registration failed: {resp.text}"
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": email_a, "password": pwd})
        assert login_resp.status_code == 200, f"User A login failed: {login_resp.text}"
        token_a = login_resp.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create User B
        email_b = f"test_notif_b_{uuid.uuid4().hex[:6]}@example.com"
        resp = await client.post(f"{BASE_URL}/auth/register", json={"email": email_b, "password": pwd, "full_name": "User B"})
        assert resp.status_code == 201, f"User B registration failed: {resp.text}"
        login_resp_b = await client.post(f"{BASE_URL}/auth/login", json={"email": email_b, "password": pwd})
        assert login_resp_b.status_code == 200, f"User B login failed: {login_resp_b.text}"
        token_b = login_resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Test 1: New user has zero notifications
        resp = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert resp.status_code == 200, f"Get notifications failed: {resp.text}"
        data = resp.json()
        assert data["total"] == 0, f"Expected 0 notifications, got {data['total']}"
        assert data["unread_count"] == 0
        print("✓ Test 1 Passed: New user has zero notifications")

        # Test 2: Unread count endpoint
        resp = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 0
        print("✓ Test 2 Passed: GET /notifications/unread-count returns 0")

        # Test 3: Solve a question with User A to trigger gamification & achievement & practice notifications
        # Get question list
        resp = await client.get(f"{BASE_URL}/practice/questions", headers=headers_a)
        assert resp.status_code == 200
        q_list = resp.json()["questions"]
        assert len(q_list) > 0
        q0 = q_list[0]
        q_id = q0["id"]

        # Solve question
        resp = await client.post(
            f"{BASE_URL}/practice/questions/{q_id}/solve",
            headers=headers_a,
            json={"solved": True, "answer": "A detailed solution answering all criteria for full points bonus test."},
        )
        assert resp.status_code == 200, f"Solve question failed: {resp.text}"
        solve_data = resp.json()
        print(f"Solved question: xp_earned={solve_data.get('xp_earned')}, current_level={solve_data.get('current_level')}")

        # Test 4: Check notifications for User A
        resp = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert resp.status_code == 200
        data_a = resp.json()
        print(f"User A has {data_a['total']} notifications. Types: {[n['type'] for n in data_a['notifications']]}")
        assert data_a["total"] >= 1, "Expected at least 1 notification after solve"
        assert data_a["unread_count"] == data_a["total"], "All new notifications should be unread"
        print("✓ Test 4 Passed: Real practice/achievement event created persistent notification")

        # Test 5: Verify User B has 0 notifications (User Isolation)
        resp = await client.get(f"{BASE_URL}/notifications", headers=headers_b)
        assert resp.status_code == 200
        data_b = resp.json()
        assert data_b["total"] == 0, f"User B should have 0 notifications, got {data_b['total']}"
        assert data_b["unread_count"] == 0
        print("✓ Test 5 Passed: User isolation verified (User B has 0 notifications)")

        # Test 6: Duplicate event protection (Idempotency)
        # Calling get_notifications again triggers sync_platform_events, which must not create duplicate notifications
        resp = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert resp.status_code == 200
        data_a_2 = resp.json()
        assert data_a_2["total"] == data_a["total"], f"Duplicates created! Was {data_a['total']}, now {data_a_2['total']}"
        print("✓ Test 6 Passed: Duplicate event protection verified (Idempotent)")

        # Test 7: Mark single notification as read
        first_notif = data_a["notifications"][0]
        notif_id = first_notif["id"]
        resp = await client.patch(f"{BASE_URL}/notifications/{notif_id}/read", headers=headers_a)
        assert resp.status_code == 200, f"Mark as read failed: {resp.text}"
        assert resp.json()["is_read"] is True

        # Check unread count decreased by 1
        resp = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == data_a["unread_count"] - 1
        print("✓ Test 7 Passed: Mark single notification as read updates unread count")

        # Test 8: User B cannot mark User A's notification as read (Ownership security)
        resp = await client.patch(f"{BASE_URL}/notifications/{notif_id}/read", headers=headers_b)
        assert resp.status_code == 404, f"Expected 404 for User B accessing User A notif, got {resp.status_code}"
        print("✓ Test 8 Passed: User B cannot mark User A notification as read (404 enforced)")

        # Test 9: Mark all notifications as read
        resp = await client.patch(f"{BASE_URL}/notifications/read-all", headers=headers_a)
        assert resp.status_code == 200, f"Mark all read failed: {resp.text}"
        resp = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 0
        print("✓ Test 9 Passed: Mark all as read resets unread count to 0")

        # Test 10: Filtering (unread_only, category, type)
        resp = await client.get(f"{BASE_URL}/notifications?unread_only=true", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0, "No unread notifications should remain after mark-all-read"

        resp = await client.get(f"{BASE_URL}/notifications?category=all", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["total"] == data_a["total"]
        print("✓ Test 10 Passed: Filtering works correctly")

        # Test 11: Server-side pagination
        resp = await client.get(f"{BASE_URL}/notifications?page=1&limit=1", headers=headers_a)
        assert resp.status_code == 200
        paged_data = resp.json()
        assert len(paged_data["notifications"]) == 1
        assert paged_data["limit"] == 1
        assert paged_data["page"] == 1
        assert paged_data["has_next"] == (data_a["total"] > 1)
        print("✓ Test 11 Passed: Server-side pagination works correctly")

        # Test 12: Delete notification
        resp = await client.delete(f"{BASE_URL}/notifications/{notif_id}", headers=headers_a)
        assert resp.status_code == 200
        # Verify it's gone
        resp = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json()["total"] == data_a["total"] - 1
        print("✓ Test 12 Passed: Delete notification works correctly")

        # Test 13: User B cannot delete User A's notification
        # Pick another notif
        remaining = resp.json()["notifications"]
        if remaining:
            other_notif_id = remaining[0]["id"]
            resp = await client.delete(f"{BASE_URL}/notifications/{other_notif_id}", headers=headers_b)
            assert resp.status_code == 404
            print("✓ Test 13 Passed: User B cannot delete User A notification (404 enforced)")

    print("\n🎉 ALL 13 BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
