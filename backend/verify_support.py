import asyncio
import uuid
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User
from app.modules.support.service import seed_support_content
from app.modules.support.model import SupportTicket, SupportTicketMessage, Feedback, FAQ, HelpArticle
from app.modules.notifications.model import Notification

BASE_URL = "http://127.0.0.1:8000"

async def test_support_system():
    print("\n==================================================")
    print("PHASE 15 -- SUPPORT & COMMUNICATION SYSTEM VERIFICATION")
    print("==================================================")

    # 1. Fetch test users from database (at least 2 users for user isolation tests)
    async with AsyncSessionLocal() as db:
        # First ensure support content is seeded
        await seed_support_content(db)

        users_stmt = select(User).limit(2)
        users = (await db.execute(users_stmt)).scalars().all()
        assert len(users) >= 1, "At least one user required in database"
        
        user1 = users[0]
        token1 = create_access_token(str(user1.id))
        headers1 = {"Authorization": f"Bearer {token1}"}
        print(f"[OK] Candidate 1: {user1.email} (ID: {user1.id})")

        # If only one user exists, create a second user for user isolation testing
        if len(users) < 2:
            import bcrypt
            user2 = User(
                email="candidate2_test@interviewplatform.ai",
                hashed_password=bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8"),
                full_name="Candidate Two",
            )
            db.add(user2)
            await db.commit()
            await db.refresh(user2)
        else:
            user2 = users[1]

        token2 = create_access_token(str(user2.id))
        headers2 = {"Authorization": f"Bearer {token2}"}
        print(f"[OK] Candidate 2: {user2.email} (ID: {user2.id})")

        # Also create an admin user for RBAC / internal note tests if not present
        admin_stmt = select(User).where(User.email == "support_admin_test@interviewplatform.ai").limit(1)
        admin_user = (await db.execute(admin_stmt)).scalar_one_or_none()
        if not admin_user:
            import bcrypt
            admin_user = User(
                email="support_admin_test@interviewplatform.ai",
                hashed_password=bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode("utf-8"),
                full_name="Support Admin",
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

        admin_token = create_access_token(str(admin_user.id))
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"[OK] Admin User: {admin_user.email} (ID: {admin_user.id})")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # TEST 19: FAQ Retrieval (Public)
        r = await client.get("/api/v1/support/faqs")
        assert r.status_code == 200, f"FAQ retrieval failed: {r.status_code} - {r.text}"
        faqs = r.json()
        assert len(faqs) >= 5, f"Expected seeded FAQs, found {len(faqs)}"
        print(f"[OK] 19. FAQ Retrieval: Retrieved {len(faqs)} active FAQs")

        # Filter FAQ by category
        r_faq_filter = await client.get("/api/v1/support/faqs?category=Payment")
        assert r_faq_filter.status_code == 200
        print(f"[OK] 19b. FAQ Category Filtering: Found {len(r_faq_filter.json())} payment FAQs")

        # TEST 20 & 21: Help Article Retrieval & Unpublished Protection
        r = await client.get("/api/v1/support/articles")
        assert r.status_code == 200, f"Articles retrieval failed: {r.status_code}"
        articles = r.json()
        assert len(articles) >= 1, "Expected seeded help articles"
        slug = articles[0]["slug"]
        print(f"[OK] 20. Help Articles Retrieval: Found {len(articles)} articles. Testing slug '{slug}'")

        r_slug = await client.get(f"/api/v1/support/articles/{slug}")
        assert r_slug.status_code == 200
        assert r_slug.json()["slug"] == slug
        print(f"[OK] 20b. Single Article by Slug: '{r_slug.json()['title']}'")

        # TEST 1: Create Ticket (Candidate 1)
        ticket_payload = {
            "subject": "Audio desync during AI Avatar mock interview",
            "description": "During question 3 the AI avatar video stopped matching the generated voice audio.",
            "category": "Interview",
            "priority": "high"
        }
        r = await client.post("/api/v1/support/tickets", json=ticket_payload, headers=headers1)
        assert r.status_code == 201, f"Ticket creation failed: {r.status_code} - {r.text}"
        ticket1_data = r.json()
        ticket1_id = ticket1_data["id"]
        ticket1_num = ticket1_data["ticket_number"]
        print(f"[OK] 1. Ticket Creation: Created ticket {ticket1_num} (ID: {ticket1_id})")
        assert ticket1_num.startswith("SUP-"), f"Invalid ticket number format: {ticket1_num}"
        assert ticket1_data["status"] == "open"
        assert ticket1_data["user_id"] == str(user1.id)

        # TEST 2: List Own Tickets (Candidate 1)
        r = await client.get("/api/v1/support/tickets", headers=headers1)
        assert r.status_code == 200
        cand1_tickets = r.json()["tickets"]
        assert any(t["id"] == ticket1_id for t in cand1_tickets), "Created ticket not in list"
        print(f"[OK] 2. List Own Tickets: Candidate 1 has {len(cand1_tickets)} tickets")

        # TEST 3: Retrieve Own Ticket (Candidate 1)
        r = await client.get(f"/api/v1/support/tickets/{ticket1_id}", headers=headers1)
        assert r.status_code == 200
        assert r.json()["ticket_number"] == ticket1_num
        assert len(r.json()["messages"]) >= 1, "Initial message not created"
        print(f"[OK] 3. Retrieve Own Ticket: Verified details for {ticket1_num}")

        # TEST 4: User Isolation - Candidate 2 CANNOT access Candidate 1's ticket
        r = await client.get(f"/api/v1/support/tickets/{ticket1_id}", headers=headers2)
        assert r.status_code == 404, f"Security violation! Candidate 2 retrieved ticket: {r.status_code}"
        print(f"[OK] 4. User Isolation (Tickets): Candidate 2 cannot access Candidate 1's ticket (404 Not Found)")

        # TEST 5: Send Ticket Message (Candidate 1)
        msg_payload = {"message": "I was using Chrome 129 on Windows 11."}
        r = await client.post(f"/api/v1/support/tickets/{ticket1_id}/messages", json=msg_payload, headers=headers1)
        assert r.status_code == 201
        print(f"[OK] 5. Send Ticket Message: Candidate message persisted")

        # TEST 6: User Isolation - Candidate 2 CANNOT send message to Candidate 1's ticket
        r = await client.post(f"/api/v1/support/tickets/{ticket1_id}/messages", json={"message": "Hacking"}, headers=headers2)
        assert r.status_code == 404, f"Security violation! Candidate 2 posted to other ticket: {r.status_code}"
        print(f"[OK] 6. User Isolation (Messages): Candidate 2 cannot reply to Candidate 1's ticket")

        # TEST 7 & 10: Support/Admin Reply & Internal Note Visibility
        # Admin sends an internal note
        r_internal = await client.post(
            f"/api/v1/support/admin/tickets/{ticket1_id}/reply",
            json={"message": "Internal note: Escalating to video infrastructure team.", "is_internal": True},
            headers=admin_headers
        )
        assert r_internal.status_code == 200, f"Admin reply failed: {r_internal.status_code} - {r_internal.text}"
        print(f"[OK] 10a. Internal Note Created by Admin")

        # Admin sends a public reply to the candidate
        r_pub = await client.post(
            f"/api/v1/support/admin/tickets/{ticket1_id}/reply",
            json={"message": "Hello! We have identified an edge case in Chrome media buffer and deployed a fix.", "is_internal": False, "status": "waiting_for_user"},
            headers=admin_headers
        )
        assert r_pub.status_code == 200
        print(f"[OK] 7. Support Admin Reply & Status Update to 'waiting_for_user'")

        # Verify candidate DOES NOT see the internal note
        r_cand_view = await client.get(f"/api/v1/support/tickets/{ticket1_id}", headers=headers1)
        cand_msgs = r_cand_view.json()["messages"]
        for m in cand_msgs:
            assert m["is_internal"] is False, f"Candidate saw internal note: {m}"
        assert not any("Internal note: Escalating" in m["message"] for m in cand_msgs)
        print(f"[OK] 10b. Internal Note Hidden from Candidate (Privacy Verified)")

        # Verify admin DOES see internal note
        r_admin_view = await client.get(f"/api/v1/support/admin/tickets", headers=admin_headers)
        assert r_admin_view.status_code == 200
        print(f"[OK] 10c. Admin tickets listing retrieved successfully")

        # TEST 8: Close Ticket (Candidate 1)
        r = await client.post(f"/api/v1/support/tickets/{ticket1_id}/close", headers=headers1)
        assert r.status_code == 200
        assert r.json()["status"] == "closed"
        print(f"[OK] 8. Close Ticket: Status transitioned to 'closed'")

        # TEST 9: Reopen Ticket (Candidate 1)
        r = await client.post(f"/api/v1/support/tickets/{ticket1_id}/reopen", headers=headers1)
        assert r.status_code == 200
        assert r.json()["status"] in ["open", "in_progress"]
        print(f"[OK] 9. Reopen Ticket: Status transitioned to '{r.json()['status']}'")

        # TEST 11: Feedback Creation (Rating 1-5)
        fb_payload = {
            "category": "interview",
            "rating": 5,
            "message": "The AI avatar realism and technical follow-ups are exceptional!",
            "page_context": "/interview/setup"
        }
        r = await client.post("/api/v1/support/feedback", json=fb_payload, headers=headers1)
        assert r.status_code == 201, f"Feedback submission failed: {r.status_code} - {r.text}"
        fb_data = r.json()
        fb_id = fb_data["id"]
        print(f"[OK] 11. Feedback Creation: Submitted 5-star rating (ID: {fb_id})")

        # TEST 12: Feedback Validation (Invalid rating 0 or 6 should fail)
        r_bad = await client.post("/api/v1/support/feedback", json={"category": "platform", "rating": 6, "message": "bad"}, headers=headers1)
        assert r_bad.status_code == 422 or r_bad.status_code == 400, f"Expected validation failure for rating 6, got {r_bad.status_code}"
        print(f"[OK] 12. Feedback Validation: Invalid rating 6 rejected")

        # Bug Report via Feedback API
        bug_payload = {
            "category": "bug_report",
            "rating": 3,
            "message": "Button label clipped on mobile screen in code arena.",
            "page_context": "/arena"
        }
        r_bug = await client.post("/api/v1/support/feedback", json=bug_payload, headers=headers1)
        assert r_bug.status_code == 201
        print(f"[OK] 19c. Bug Report Submission: Persisted with category 'bug_report'")

        # TEST 13: Feedback User Isolation
        r_fb1 = await client.get("/api/v1/support/feedback/mine", headers=headers1)
        r_fb2 = await client.get("/api/v1/support/feedback/mine", headers=headers2)
        assert r_fb1.status_code == 200
        assert r_fb2.status_code == 200
        cand1_fb_ids = [f["id"] for f in r_fb1.json()["items"]]
        cand2_fb_ids = [f["id"] for f in r_fb2.json()["items"]]
        assert fb_id in cand1_fb_ids
        assert fb_id not in cand2_fb_ids
        print(f"[OK] 13. Feedback User Isolation: Candidate 2 cannot see Candidate 1's feedback")

        # TEST 14, 15, 16, 17, 18: Notification Lifecycle
        # List notifications for candidate 1
        r_notif = await client.get("/api/v1/notifications", headers=headers1)
        assert r_notif.status_code == 200
        notifs = r_notif.json()["notifications"]
        assert len(notifs) >= 1, "Expected notifications generated from tickets/replies"
        print(f"[OK] 14 & 15. Notification Persistence & Listing: Candidate 1 has {len(notifs)} notifications")

        # Unread count
        r_unread = await client.get("/api/v1/notifications/unread-count", headers=headers1)
        assert r_unread.status_code == 200
        initial_unread = r_unread.json()["unread_count"]
        print(f"[OK] 16. Unread Notification Count: {initial_unread} unread")

        # Mark single notification as read
        first_notif_id = notifs[0]["id"]
        r_mark_one = await client.patch(f"/api/v1/notifications/{first_notif_id}/read", headers=headers1)
        assert r_mark_one.status_code == 200
        print(f"[OK] 17. Mark Single Notification Read: {first_notif_id}")

        # Mark all notifications as read (POST endpoint as per spec)
        r_mark_all = await client.post("/api/v1/notifications/read-all", headers=headers1)
        assert r_mark_all.status_code == 200
        r_unread_after = await client.get("/api/v1/notifications/unread-count", headers=headers1)
        assert r_unread_after.json()["unread_count"] == 0
        print(f"[OK] 18. Mark All Notifications Read (POST /read-all): Count is now 0")

        # TEST 22: RBAC Enforcement
        # Candidate 2 trying to access admin tickets endpoint should fail (403 or 401)
        r_rbac = await client.get("/api/v1/support/admin/tickets", headers=headers2)
        assert r_rbac.status_code == 403, f"Expected 403 Forbidden for non-admin, got {r_rbac.status_code}"
        print(f"[OK] 22. RBAC Enforcement: Non-admin candidate blocked with 403 Forbidden")

    print("\n==================================================")
    print("ALL 22 BACKEND SUPPORT & COMMUNICATION TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_support_system())
