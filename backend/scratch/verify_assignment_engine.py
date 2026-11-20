import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath("."))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User
from app.modules.notifications.model import Notification
from sqlalchemy import select, and_

async def test_assignment_engine():
    print("============================================================")
    print("PHASE 20: CANDIDATE ASSIGNMENT ENGINE VERIFICATION SUITE")
    print("============================================================")

    async with AsyncSessionLocal() as db:
        admin_res = await db.execute(select(User).where(User.role == "SUPER_ADMIN").limit(1))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_res = await db.execute(select(User).where(User.role == "ADMIN").limit(1))
            admin_user = admin_res.scalar_one_or_none()

        cands_res = await db.execute(select(User).where(User.role == "CANDIDATE").limit(2))
        cands = list(cands_res.scalars().all())

    assert admin_user is not None, "Admin user must exist"
    assert len(cands) >= 1, "At least one candidate must exist"
    cand_a = cands[0]
    cand_b = cands[1] if len(cands) > 1 else None

    print(f"Verified Admin: {admin_user.email} ({admin_user.id})")
    print(f"Verified Candidate A: {cand_a.email} ({cand_a.id})")
    if cand_b:
        print(f"Verified Candidate B: {cand_b.email} ({cand_b.id})")

    admin_token = create_access_token(str(admin_user.id))
    cand_a_token = create_access_token(str(cand_a.id))
    cand_b_token = create_access_token(str(cand_b.id)) if cand_b else None

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"} if cand_b_token else {}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # TEST 1: Individual candidate assignment (Coding Problem)
        print("\n[TEST 1] Admin assigns coding problem to Candidate A...")
        due_tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        payload_1 = {
            "title": f"Algorithm Sprint: Dynamic Programming {uuid.uuid4().hex[:4]}",
            "description": "Master the knapsack and longest common subsequence patterns.",
            "assignment_type": "CODING_PROBLEM",
            "content_id": "maximum-subarray",
            "priority": "HIGH",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": str(cand_a.id)},
            "due_date": due_tomorrow.isoformat(),
            "time_limit_mins": 45,
            "attempt_limit": 3,
            "instructions": "Write optimal O(n) Kadane algorithm implementation.",
        }
        res1 = await client.post("/api/v1/admin/assignments", json=payload_1, headers=admin_headers)
        assert res1.status_code in [200, 201], f"Failed to create assignment: {res1.text}"
        assign_1_data = res1.json()
        assign_1_id = assign_1_data["id"]
        print(f"   SUCCESS: Created assignment ID: {assign_1_id}, Title: {assign_1_data['title']}")

        # TEST 2: Notification delivered to Candidate A
        print("\n[TEST 2] Verifying notification created for Candidate A...")
        async with AsyncSessionLocal() as db:
            n_res = await db.execute(
                select(Notification).where(
                    and_(Notification.user_id == cand_a.id, Notification.title.ilike("%New Task Assigned%"))
                ).order_by(Notification.created_at.desc()).limit(1)
            )
            notif = n_res.scalar_one_or_none()
            assert notif is not None, "Notification record was not created for Candidate A"
            print(f"   SUCCESS: Notification verified! Message: '{notif.message}'")

        # TEST 3: Candidate A checks inbox
        print("\n[TEST 3] Candidate A fetches assigned tasks via GET /api/v1/candidate/assignments...")
        res3 = await client.get("/api/v1/candidate/assignments", headers=cand_a_headers)
        assert res3.status_code == 200, f"Candidate inbox failed: {res3.text}"
        tasks = res3.json()
        assert len(tasks) > 0, "No tasks returned in candidate inbox"
        task_match = next((t for t in tasks if t["assignment_id"] == assign_1_id), None)
        assert task_match is not None, f"Task {assign_1_id} not found in candidate inbox"
        assert task_match["status"] == "ASSIGNED"
        assert task_match["priority"] == "HIGH"
        print(f"   SUCCESS: Candidate inbox received task: '{task_match['title']}', Status: {task_match['status']}")

        # TEST 4: Candidate A starts the assignment
        print("\n[TEST 4] Candidate A starts the assignment...")
        res4 = await client.post(f"/api/v1/candidate/assignments/{assign_1_id}/start", headers=cand_a_headers)
        assert res4.status_code == 200, f"Start assignment failed: {res4.text}"
        start_data = res4.json()
        assert start_data["status"] == "IN_PROGRESS"
        assert start_data["attempt_count"] == 1
        print(f"   SUCCESS: Assignment status updated to IN_PROGRESS, Attempts: {start_data['attempt_count']}")

        # TEST 5: IDOR Security Protection (Candidate B cannot touch Candidate A's assignment)
        if cand_b_headers:
            print("\n[TEST 5] Security Check: Candidate B attempts unauthorized access to Candidate A's assignment...")
            res_idor = await client.post(f"/api/v1/candidate/assignments/{assign_1_id}/start", headers=cand_b_headers)
            assert res_idor.status_code in [403, 404], f"IDOR vulnerability! Expected 403/404, got {res_idor.status_code}"
            print(f"   SUCCESS: IDOR blocked! Candidate B received HTTP {res_idor.status_code}")

        # TEST 6: Candidate A submits assignment completion
        print("\n[TEST 6] Candidate A submits completion with score 94.5%...")
        submit_payload = {
            "score": 94.5,
            "submission_ref_id": str(uuid.uuid4()),
            "submission_data": {"passed_tests": 15, "total_tests": 15, "language": "python"}
        }
        res6 = await client.post(f"/api/v1/candidate/assignments/{assign_1_id}/submit", json=submit_payload, headers=cand_a_headers)
        assert res6.status_code == 200, f"Submit assignment failed: {res6.text}"
        submit_data = res6.json()
        assert submit_data["status"] == "COMPLETED"
        assert submit_data["score"] == 94.5
        print(f"   SUCCESS: Assignment submitted and marked COMPLETED with score {submit_data['score']}%")

        # TEST 7: Role-based cohort assignment (Target: ROLE = CANDIDATE)
        print("\n[TEST 7] Admin creates Role-based cohort assignment for all candidates...")
        payload_cohort = {
            "title": f"System Architecture Mock Assessment {uuid.uuid4().hex[:4]}",
            "description": "Design an event-driven notification engine for 10M DAU.",
            "assignment_type": "AI_INTERVIEW",
            "priority": "URGENT",
            "target_type": "ROLE",
            "target_filter": {"role": "CANDIDATE"},
            "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "time_limit_mins": 30,
            "attempt_limit": 1,
            "instructions": "Demonstrate understanding of Kafka, message partitioning, and DLQs.",
        }
        res7 = await client.post("/api/v1/admin/assignments", json=payload_cohort, headers=admin_headers)
        assert res7.status_code in [200, 201], f"Role assignment failed: {res7.text}"
        cohort_assign_id = res7.json()["id"]
        print(f"   SUCCESS: Created Role cohort assignment ID: {cohort_assign_id}")

        # TEST 8: Admin checks assignment telemetry detail
        print("\n[TEST 8] Admin views assignment telemetry detail...")
        res8 = await client.get(f"/api/v1/admin/assignments/{assign_1_id}", headers=admin_headers)
        assert res8.status_code == 200, f"Telemetry detail failed: {res8.text}"
        detail = res8.json()
        assert detail["total_completed"] == 1
        assert detail["avg_score"] == 94.5
        assert len(detail["recipients"]) > 0
        cand_progress = detail["recipients"][0]
        assert cand_progress["status"] == "COMPLETED"
        assert cand_progress["score"] == 94.5
        print(f"   SUCCESS: Telemetry accurately shows: 1 Completed, Avg Score: {detail['avg_score']}%, Rate: {detail['completion_rate']}%")

        # TEST 9: Admin views global assignment analytics
        print("\n[TEST 9] Admin queries global assignment analytics...")
        res9 = await client.get("/api/v1/admin/assignments/analytics", headers=admin_headers)
        assert res9.status_code == 200, f"Analytics query failed: {res9.text}"
        analytics = res9.json()
        assert analytics["total_assignments"] >= 2
        assert analytics["total_task_dispatches"] >= 2
        print(f"   SUCCESS: Global Analytics: Total Assignments: {analytics['total_assignments']}, Dispatches: {analytics['total_task_dispatches']}, By Type: {analytics['by_type']}")

    print("\n============================================================")
    print(">>> ALL 9 ASSIGNMENT ENGINE VERIFICATIONS PASSED 100%! <<<")
    print("============================================================")
    return True

if __name__ == "__main__":
    asyncio.run(test_assignment_engine())
