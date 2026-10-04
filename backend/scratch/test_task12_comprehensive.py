import asyncio
import sys
import uuid
import httpx

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_full_system():
    print("==================================================")
    print("TASK 12 — COMPLETE PRODUCTION VERIFICATION SUITE")
    print("==================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Authentication & User Isolation Setup
        email_a = f"candidate_a_{uuid.uuid4().hex[:6]}@example.com"
        email_b = f"candidate_b_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "ProductionPassword123!"

        # Register User A
        r = await client.post(f"{BASE_URL}/auth/register", json={"email": email_a, "password": pwd, "full_name": "Candidate A"})
        assert r.status_code == 201
        l = await client.post(f"{BASE_URL}/auth/login", json={"email": email_a, "password": pwd})
        token_a = l.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register User B
        r = await client.post(f"{BASE_URL}/auth/register", json={"email": email_b, "password": pwd, "full_name": "Candidate B"})
        assert r.status_code == 201
        l = await client.post(f"{BASE_URL}/auth/login", json={"email": email_b, "password": pwd})
        token_b = l.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        print("[PASS] 1. Authentication & user creation verified")

        # Step 2: Empty initial state
        res_a = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["total"] == 0
        assert data_a["unread_count"] == 0
        assert len(data_a["notifications"]) == 0

        res_count = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert res_count.status_code == 200
        assert res_count.json()["unread_count"] == 0
        print("[PASS] 2. Initial state verified: New user has exactly 0 notifications & 0 unread")

        # Step 3: Trigger real practice events (Solve questions)
        q_res = await client.get(f"{BASE_URL}/practice/questions?limit=5", headers=headers_a)
        assert q_res.status_code == 200
        questions = q_res.json()["questions"]
        assert len(questions) >= 2

        # Solve Q1 with full detailed answer
        s1 = await client.post(
            f"{BASE_URL}/practice/questions/{questions[0]['id']}/solve",
            headers=headers_a,
            json={"solved": True, "answer": "Detailed solution explaining core mechanisms, trade-offs and complexity analysis for full points."},
        )
        assert s1.status_code == 200

        # Step 4: Verify real notifications generated
        res_after = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert res_after.status_code == 200
        data_after = res_after.json()
        types = [n["type"] for n in data_after["notifications"]]
        print(f"Generated notification types: {types}")
        assert len(data_after["notifications"]) >= 2
        assert "XP_EARNED" in types
        assert "ACHIEVEMENT_UNLOCKED" in types or "MISSION_COMPLETED" in types
        initial_unread = data_after["unread_count"]
        assert initial_unread == data_after["total"]
        print(f"[PASS] 3. Real event integration verified: {data_after['total']} persistent notifications created")

        # Step 5: Duplicate Protection (Idempotency)
        # Calling notifications again triggers sync_platform_events; total must remain identical
        res_sync = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert res_sync.status_code == 200
        assert res_sync.json()["total"] == data_after["total"]
        print("[PASS] 4. Duplicate protection verified: Repeated sync calls produce 0 duplicate records")

        # Step 6: User Isolation Verification
        res_b = await client.get(f"{BASE_URL}/notifications", headers=headers_b)
        assert res_b.status_code == 200
        assert res_b.json()["total"] == 0
        assert res_b.json()["unread_count"] == 0

        # Attempt User B accessing User A's notification
        first_notif_id = data_after["notifications"][0]["id"]
        res_b_tamper = await client.patch(f"{BASE_URL}/notifications/{first_notif_id}/read", headers=headers_b)
        assert res_b_tamper.status_code == 404, f"Expected 404, got {res_b_tamper.status_code}"

        res_b_del_tamper = await client.delete(f"{BASE_URL}/notifications/{first_notif_id}", headers=headers_b)
        assert res_b_del_tamper.status_code == 404
        print("[PASS] 5. User isolation verified: User B has 0 notifications and cannot access/modify User A's data (404 enforced)")

        # Step 7: Mark Single as Read
        mark_res = await client.patch(f"{BASE_URL}/notifications/{first_notif_id}/read", headers=headers_a)
        assert mark_res.status_code == 200
        assert mark_res.json()["is_read"] is True

        unread_check = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert unread_check.status_code == 200
        assert unread_check.json()["unread_count"] == initial_unread - 1
        print("[PASS] 6. Mark single as read verified: Unread count decrements accurately")

        # Step 8: Mark All as Read
        read_all_res = await client.patch(f"{BASE_URL}/notifications/read-all", headers=headers_a)
        assert read_all_res.status_code == 200
        assert read_all_res.json()["updated_count"] >= 1

        unread_after_all = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers_a)
        assert unread_after_all.status_code == 200
        assert unread_after_all.json()["unread_count"] == 0
        print("[PASS] 7. Mark all as read verified: All notifications marked read, unread count = 0")

        # Step 9: Filtering
        res_unread_filter = await client.get(f"{BASE_URL}/notifications?unread_only=true", headers=headers_a)
        assert res_unread_filter.status_code == 200
        assert res_unread_filter.json()["total"] == 0

        res_cat_ach = await client.get(f"{BASE_URL}/notifications?category=achievements", headers=headers_a)
        assert res_cat_ach.status_code == 200
        for n in res_cat_ach.json()["notifications"]:
            assert n["category"] == "Achievements"

        print("[PASS] 8. Category & unread filtering verified: Filter criteria strictly respected")

        # Step 10: Server-side Pagination
        res_page_1 = await client.get(f"{BASE_URL}/notifications?page=1&limit=1", headers=headers_a)
        assert res_page_1.status_code == 200
        p1_data = res_page_1.json()
        assert len(p1_data["notifications"]) == 1
        assert p1_data["page"] == 1
        assert p1_data["limit"] == 1
        assert p1_data["has_next"] is True

        res_page_2 = await client.get(f"{BASE_URL}/notifications?page=2&limit=1", headers=headers_a)
        assert res_page_2.status_code == 200
        p2_data = res_page_2.json()
        assert len(p2_data["notifications"]) == 1
        assert p2_data["page"] == 2
        assert p1_data["notifications"][0]["id"] != p2_data["notifications"][0]["id"]
        print("[PASS] 9. Server-side pagination verified: Sequential distinct pages with authoritative bounds")

        # Step 11: Real Interview Completion Notification
        # Create an interview session for User A
        setup_res = await client.post(
            f"{BASE_URL}/interview",
            headers=headers_a,
            json={"job_role": "Backend Lead", "difficulty": "Hard", "experience_level": "Senior", "interview_type": "Technical"},
        )
        assert setup_res.status_code == 201
        interview_id = setup_res.json()["interview"]["id"]
        # Start interview
        start_res = await client.post(f"{BASE_URL}/interview/{interview_id}/start", headers=headers_a)
        assert start_res.status_code == 200
        # Submit answers
        ans_res = await client.post(
            f"{BASE_URL}/interview/{interview_id}/answers",
            headers=headers_a,
            json={"answers": "Candidate answers explaining distributed architecture, caching, and resiliency."},
        )
        assert ans_res.status_code == 200
        # Complete interview
        comp_res = await client.post(
            f"{BASE_URL}/interview/{interview_id}/complete",
            headers=headers_a,
            json={"score": 92.0},
        )
        assert comp_res.status_code == 200

        # Check for interview notification
        notif_int = await client.get(f"{BASE_URL}/notifications?category=interviews", headers=headers_a)
        assert notif_int.status_code == 200
        int_notifs = notif_int.json()["notifications"]
        assert len(int_notifs) >= 1
        assert int_notifs[0]["type"] == "INTERVIEW_COMPLETED"
        print("[PASS] 10. Real interview completion event verified: Generated INTERVIEW_COMPLETED notification")

        # Step 12: Delete notification
        del_res = await client.delete(f"{BASE_URL}/notifications/{first_notif_id}", headers=headers_a)
        assert del_res.status_code == 200
        verify_gone = await client.get(f"{BASE_URL}/notifications", headers=headers_a)
        assert all(n["id"] != first_notif_id for n in verify_gone.json()["notifications"])
        print("[PASS] 11. Notification deletion verified: Record permanently removed with ownership validation")

    print("\n==================================================")
    print("ALL 11 PRODUCTION VERIFICATION PHASES PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_full_system())
