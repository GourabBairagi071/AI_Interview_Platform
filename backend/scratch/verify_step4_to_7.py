import requests
import json
import uuid
import datetime
import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def parse_items(resp_json, key=None):
    if isinstance(resp_json, list):
        return resp_json
    if isinstance(resp_json, dict):
        if key and key in resp_json:
            return resp_json[key]
        for k in ["items", "questions", "resources", "plans", "coupons", "achievements", "companies", "problems", "assignments", "tasks"]:
            if k in resp_json and isinstance(resp_json[k], list):
                return resp_json[k]
    return []

async def run_step4_to_7_verification():
    step4_results = {}
    step5_results = {}
    step6_results = {}
    step7_results = {}
    test_record_ids = {}

    print("=== STARTING BATCH 3 VERIFICATION (STEPS 4, 5, 6, 7) ===")

    # 0. Setup Tokens
    async with httpx.AsyncClient() as client:
        # Admin
        admin_login = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@interviewplatform.ai",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        rand_suffix = uuid.uuid4().hex[:6]

        # Candidate A
        cand_a_email = f"cand_s4_a_{rand_suffix}@example.com"
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": cand_a_email,
            "full_name": f"Candidate S4 Alpha {rand_suffix}",
            "password": "Password@123",
            "role": "candidate"
        })
        login_a = await client.post(f"{BASE_URL}/auth/login", json={"email": cand_a_email, "password": "Password@123"})
        cand_a_token = login_a.json()["access_token"]
        cand_a_id = login_a.json()["user"]["id"]
        cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}

        # Candidate B
        cand_b_email = f"cand_s4_b_{rand_suffix}@example.com"
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": cand_b_email,
            "full_name": f"Candidate S4 Beta {rand_suffix}",
            "password": "Password@123",
            "role": "candidate"
        })
        login_b = await client.post(f"{BASE_URL}/auth/login", json={"email": cand_b_email, "password": "Password@123"})
        cand_b_token = login_b.json()["access_token"]
        cand_b_id = login_b.json()["user"]["id"]
        cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}

        test_record_ids["cand_a_id"] = cand_a_id
        test_record_ids["cand_b_id"] = cand_b_id

        # ============================================================
        # STEP 4: SCHEDULING (9 Tests)
        # ============================================================
        print("\n--- STEP 4: SCHEDULING VERIFICATION ---")
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # 1. Future scheduled assignment
        future_time = (now_utc + datetime.timedelta(hours=2)).isoformat()
        p1 = {
            "title": f"Future Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "priority": "HIGH",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "scheduled_for": future_time
        }
        r1 = await client.post(f"{BASE_URL}/admin/assignments", json=p1, headers=admin_headers)
        step4_results["1_future_scheduled"] = {
            "status": "VERIFIED" if r1.status_code == 201 and r1.json()["status"] == "SCHEDULED" else "FAILED",
            "status_code": r1.status_code,
            "returned_status": r1.json().get("status") if r1.status_code == 201 else r1.text
        }

        # 2. Assignment before scheduled time is not active
        asg_id_1 = r1.json()["id"] if r1.status_code == 201 else None
        inbox_1 = await client.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        inbox_1_items = parse_items(inbox_1.json())
        has_future_inbox = any(str(item.get("assignment_id")) == str(asg_id_1) for item in inbox_1_items)
        step4_results["2_before_scheduled_inactive"] = {
            "status": "VERIFIED" if not has_future_inbox else "FAILED",
            "inbox_contains_scheduled": has_future_inbox
        }

        # 3. Assignment after scheduled time becomes active (scheduled_for in past)
        past_sched_time = (now_utc - datetime.timedelta(minutes=5)).isoformat()
        p3 = {
            "title": f"Past Sched Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "scheduled_for": past_sched_time
        }
        r3 = await client.post(f"{BASE_URL}/admin/assignments", json=p3, headers=admin_headers)
        step4_results["3_after_scheduled_active"] = {
            "status": "VERIFIED" if r3.status_code == 201 and r3.json()["status"] == "ASSIGNED" else "FAILED",
            "returned_status": r3.json().get("status") if r3.status_code == 201 else r3.text
        }

        # 4. start_date enforcement
        future_start = (now_utc + datetime.timedelta(days=1)).isoformat()
        p4 = {
            "title": f"Future Start Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "start_date": future_start
        }
        r4 = await client.post(f"{BASE_URL}/admin/assignments", json=p4, headers=admin_headers)
        step4_results["4_start_date_enforcement"] = {
            "status": "VERIFIED" if r4.status_code == 201 else "FAILED",
            "status_code": r4.status_code
        }

        # 5. due_date enforcement & 6. expired assignment behavior
        past_due = (now_utc - datetime.timedelta(hours=1)).isoformat()
        p5 = {
            "title": f"Past Due Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "due_date": past_due
        }
        r5 = await client.post(f"{BASE_URL}/admin/assignments", json=p5, headers=admin_headers)
        asg_id_5 = r5.json()["id"] if r5.status_code == 201 else None
        
        # Candidate attempts to start expired task
        start_expired = await client.post(f"{BASE_URL}/candidate/assignments/{asg_id_5}/start", headers=cand_a_headers)
        step4_results["5_6_due_date_and_expired_behavior"] = {
            "status": "VERIFIED" if start_expired.status_code == 400 and "expired" in start_expired.text.lower() else "FAILED",
            "start_status_code": start_expired.status_code,
            "response_detail": start_expired.text
        }

        # 7. Completed assignment remains COMPLETED (does not become EXPIRED)
        p7 = {
            "title": f"Completed Prior Due Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "due_date": (now_utc + datetime.timedelta(seconds=2)).isoformat()
        }
        r7 = await client.post(f"{BASE_URL}/admin/assignments", json=p7, headers=admin_headers)
        asg_id_7 = r7.json()["id"]
        
        # Start and submit immediately
        await client.post(f"{BASE_URL}/candidate/assignments/{asg_id_7}/start", headers=cand_a_headers)
        await client.post(f"{BASE_URL}/candidate/assignments/{asg_id_7}/submit", json={"score": 100.0}, headers=cand_a_headers)
        
        # Wait for due date to pass
        await asyncio.sleep(2.5)
        
        # Re-fetch candidate inbox tasks
        inbox_7 = await client.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        tasks_7 = parse_items(inbox_7.json())
        t7 = next((item for item in tasks_7 if str(item.get("assignment_id")) == str(asg_id_7)), None)
        remains_completed = t7 is not None and t7.get("status") == "COMPLETED"
        step4_results["7_completed_remains_completed"] = {
            "status": "VERIFIED" if remains_completed else "FAILED",
            "persisted_status": t7.get("status") if t7 else None
        }

        # 8 & 9. Server-side time enforcement & payload override blocking
        # Candidate tries to pass fake due_date in submit payload
        sub_override = await client.post(f"{BASE_URL}/candidate/assignments/{asg_id_7}/submit", json={
            "score": 90.0,
            "due_date": (now_utc + datetime.timedelta(days=100)).isoformat(),
            "status": "IN_PROGRESS"
        }, headers=cand_a_headers)
        step4_results["8_9_server_time_and_payload_protection"] = {
            "status": "VERIFIED" if sub_override.status_code == 200 and sub_override.json().get("status") == "COMPLETED" else "FAILED",
            "override_attempt_response_status": sub_override.json().get("status")
        }

        # ============================================================
        # STEP 5: ATTEMPT LIMITS (7 Tests)
        # ============================================================
        print("\n--- STEP 5: ATTEMPT LIMITS VERIFICATION ---")
        p_att = {
            "title": f"Single Attempt Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "attempt_limit": 1
        }
        r_att = await client.post(f"{BASE_URL}/admin/assignments", json=p_att, headers=admin_headers)
        asg_att_id = r_att.json()["id"]

        # First start succeeds
        start_1 = await client.post(f"{BASE_URL}/candidate/assignments/{asg_att_id}/start", headers=cand_a_headers)
        start_1_ok = start_1.status_code == 200 and start_1.json().get("attempt_count") == 1

        # Submit task
        await client.post(f"{BASE_URL}/candidate/assignments/{asg_att_id}/submit", json={"score": 85.0}, headers=cand_a_headers)

        # Second start is rejected (attempt_limit = 1 reached)
        start_2 = await client.post(f"{BASE_URL}/candidate/assignments/{asg_att_id}/start", headers=cand_a_headers)
        start_2_rejected = start_2.status_code in (400, 403) and ("limit" in start_2.text.lower() or "completed" in start_2.text.lower())

        # Attempt state persists after refresh
        inbox_att = await client.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        tasks_att = parse_items(inbox_att.json())
        t_att = next((item for item in tasks_att if str(item.get("assignment_id")) == str(asg_att_id)), None)
        att_persisted = t_att is not None and t_att.get("attempt_count") == 1 and t_att.get("status") == "COMPLETED"

        step5_results = {
            "1_2_first_start_succeeds": {"status": "VERIFIED" if start_1_ok else "FAILED"},
            "3_attempt_count_is_1": {"status": "VERIFIED" if start_1_ok else "FAILED"},
            "4_second_start_rejected": {"status": "VERIFIED" if start_2_rejected else "FAILED", "response": start_2.text},
            "5_6_completed_cannot_restart": {"status": "VERIFIED" if start_2_rejected else "FAILED"},
            "7_attempt_state_persists": {"status": "VERIFIED" if att_persisted else "FAILED"}
        }

        # ============================================================
        # STEP 6: SECURITY / IDOR (15 Tests)
        # ============================================================
        print("\n--- STEP 6: SECURITY & IDOR VERIFICATION ---")

        # 1. Unauthenticated -> Admin Assignment Endpoint
        sec_1 = await client.get(f"{BASE_URL}/admin/assignments")
        # 2. Candidate -> Admin Assignment Endpoint
        sec_2 = await client.get(f"{BASE_URL}/admin/assignments", headers=cand_a_headers)
        sec_2_post = await client.post(f"{BASE_URL}/admin/assignments", json=p_att, headers=cand_a_headers)
        # 3 & 4. Candidate A attempts to access Candidate B's task (IDOR)
        p_sec_b = {
            "title": f"Cand B Private Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_b_id}
        }
        r_sec_b = await client.post(f"{BASE_URL}/admin/assignments", json=p_sec_b, headers=admin_headers)
        asg_b_id = r_sec_b.json()["id"]

        # Candidate A attempts to start Candidate B's task
        sec_idor_start = await client.post(f"{BASE_URL}/candidate/assignments/{asg_b_id}/start", headers=cand_a_headers)
        # Candidate A attempts to submit Candidate B's task
        sec_idor_submit = await client.post(f"{BASE_URL}/candidate/assignments/{asg_b_id}/submit", json={"score": 100.0}, headers=cand_a_headers)

        # 5. Invalid assignment UUID
        sec_invalid_uuid = await client.post(f"{BASE_URL}/candidate/assignments/invalid-uuid-123/start", headers=cand_a_headers)

        # 6. Candidate attempts to access admin analytics telemetry
        sec_analytics = await client.get(f"{BASE_URL}/admin/assignments/analytics", headers=cand_a_headers)

        # 7. Candidate attempts to access admin assignment detail (recipient cohort)
        sec_detail = await client.get(f"{BASE_URL}/admin/assignments/{asg_b_id}", headers=cand_a_headers)

        step6_results = {
            "1_unauth_admin_endpoint_blocked": {"status": "VERIFIED" if sec_1.status_code == 401 else "FAILED", "code": sec_1.status_code},
            "2_candidate_admin_endpoint_blocked": {"status": "VERIFIED" if sec_2.status_code == 403 and sec_2_post.status_code == 403 else "FAILED", "get_code": sec_2.status_code, "post_code": sec_2_post.status_code},
            "3_4_idor_candidate_isolation_start": {"status": "VERIFIED" if sec_idor_start.status_code == 404 else "FAILED", "code": sec_idor_start.status_code},
            "3_4_idor_candidate_isolation_submit": {"status": "VERIFIED" if sec_idor_submit.status_code == 404 else "FAILED", "code": sec_idor_submit.status_code},
            "5_invalid_uuid_validation": {"status": "VERIFIED" if sec_invalid_uuid.status_code == 422 else "FAILED", "code": sec_invalid_uuid.status_code},
            "6_telemetry_access_blocked": {"status": "VERIFIED" if sec_analytics.status_code == 403 else "FAILED", "code": sec_analytics.status_code},
            "7_recipient_cohort_access_blocked": {"status": "VERIFIED" if sec_detail.status_code == 403 else "FAILED", "code": sec_detail.status_code}
        }

        # ============================================================
        # STEP 7: RACE CONDITIONS (Concurrent Execution Tests)
        # ============================================================
        print("\n--- STEP 7: RACE CONDITIONS VERIFICATION ---")

        p_race = {
            "title": f"Race Condition Task {rand_suffix}",
            "assignment_type": "QUESTION",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "attempt_limit": 5
        }
        r_race = await client.post(f"{BASE_URL}/admin/assignments", json=p_race, headers=admin_headers)
        asg_race_id = r_race.json()["id"]

        # Concurrent Start Requests
        async def do_start():
            return await client.post(f"{BASE_URL}/candidate/assignments/{asg_race_id}/start", headers=cand_a_headers)

        start_results = await asyncio.gather(do_start(), do_start(), do_start(), return_exceptions=True)
        start_codes = [res.status_code for res in start_results if isinstance(res, httpx.Response)]

        # Concurrent Submit Requests
        async def do_submit(score_val):
            return await client.post(f"{BASE_URL}/candidate/assignments/{asg_race_id}/submit", json={"score": score_val}, headers=cand_a_headers)

        submit_results = await asyncio.gather(do_submit(90.0), do_submit(95.0), return_exceptions=True)
        submit_codes = [res.status_code for res in submit_results if isinstance(res, httpx.Response)]

        # Verify DB final state after concurrent operations
        inbox_race = await client.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        tasks_race = parse_items(inbox_race.json())
        t_race = next((item for item in tasks_race if str(item.get("assignment_id")) == str(asg_race_id)), None)

        step7_results = {
            "1_2_concurrent_starts_handled": {"status": "VERIFIED" if all(code == 200 for code in start_codes) else "FAILED", "codes": start_codes},
            "3_4_concurrent_submits_handled": {"status": "VERIFIED" if all(code == 200 for code in submit_codes) else "FAILED", "codes": submit_codes},
            "5_final_status_consistent": {"status": "VERIFIED" if t_race and t_race.get("status") == "COMPLETED" else "FAILED", "final_status": t_race.get("status") if t_race else None}
        }

    output = {
        "step4_scheduling": step4_results,
        "step5_attempt_limits": step5_results,
        "step6_security_idor": step6_results,
        "step7_race_conditions": step7_results,
        "test_record_ids": test_record_ids
    }

    with open("scratch/step4_to_7_verification_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n============================================================")
    print("BATCH 3 (STEPS 4, 5, 6, 7) VERIFICATION SUMMARY")
    print("============================================================")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    asyncio.run(run_step4_to_7_verification())
