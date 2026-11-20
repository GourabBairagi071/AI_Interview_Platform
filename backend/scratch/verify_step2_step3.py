import requests
import json
import uuid
import datetime

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

def run_step2_step3_verification():
    results_step2 = {}
    results_step3 = {}
    test_record_ids = {}

    print("=== STARTING STEP 2 & STEP 3 VERIFICATION ===")

    # 0. Auth Setup: Admin + 2 Candidate Accounts for Isolation & Targeting Tests
    admin_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    rand_suffix = uuid.uuid4().hex[:6]

    # Candidate A
    cand_a_email = f"cand_a_{rand_suffix}@example.com"
    reg_a = requests.post(f"{BASE_URL}/auth/register", json={
        "email": cand_a_email,
        "full_name": f"Candidate Alpha {rand_suffix}",
        "password": "Password@123",
        "role": "candidate"
    })
    login_a = requests.post(f"{BASE_URL}/auth/login", json={"email": cand_a_email, "password": "Password@123"})
    assert login_a.status_code == 200, f"Candidate A login failed: {login_a.text}"
    cand_a_token = login_a.json()["access_token"]
    cand_a_id = login_a.json()["user"]["id"]
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}

    # Candidate B
    cand_b_email = f"cand_b_{rand_suffix}@example.com"
    reg_b = requests.post(f"{BASE_URL}/auth/register", json={
        "email": cand_b_email,
        "full_name": f"Candidate Beta {rand_suffix}",
        "password": "Password@123",
        "role": "candidate"
    })
    login_b = requests.post(f"{BASE_URL}/auth/login", json={"email": cand_b_email, "password": "Password@123"})
    assert login_b.status_code == 200, f"Candidate B login failed: {login_b.text}"
    cand_b_token = login_b.json()["access_token"]
    cand_b_id = login_b.json()["user"]["id"]
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}

    test_record_ids["candidate_a_id"] = cand_a_id
    test_record_ids["candidate_b_id"] = cand_b_id

    # Update Candidate A skill profile for SKILL targeting test
    requests.put(f"{BASE_URL}/profile/me", json={"skills": ["Python", "FastAPI", "System Design"]}, headers=cand_a_headers)

    print(f"Auth Setup Complete. Cand A: {cand_a_id}, Cand B: {cand_b_id}")

    # ============================================================
    # STEP 2 — VERIFY 12 ASSIGNMENT TYPES
    # ============================================================
    assignment_types = [
        "QUESTION",
        "CODING_PROBLEM",
        "PRACTICE_SET",
        "MOCK_TEST",
        "AI_INTERVIEW",
        "INTERVIEW_TEMPLATE",
        "RESOURCE",
        "ROADMAP",
        "COMPANY_PREPARATION",
        "CONTEST",
        "CUSTOM_TASK",
        "ASSESSMENT"
    ]

    print("\n============================================================")
    print("STEP 2: TESTING ALL 12 ASSIGNMENT TYPES (END-TO-END FLOW)")
    print("============================================================")

    for atype in assignment_types:
        print(f"\n--- Testing Assignment Type: {atype} ---")
        title = f"QA Task {atype} {rand_suffix}"
        payload = {
            "title": title,
            "description": f"Verification task for assignment type {atype}",
            "assignment_type": atype,
            "content_id": f"content-{atype.lower()}-01",
            "content_payload": {"sample_key": "sample_val", "type": atype},
            "instructions": f"Instructions for {atype}",
            "priority": "HIGH",
            "target_type": "INDIVIDUAL",
            "target_filter": {"candidate_id": cand_a_id},
            "due_date": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat(),
            "time_limit_mins": 45,
            "attempt_limit": 2
        }

        # 1. Admin Create
        c_res = requests.post(f"{BASE_URL}/admin/assignments", json=payload, headers=admin_headers)
        if c_res.status_code not in (200, 201):
            results_step2[atype] = {"status": "FAILED", "stage": "CREATE", "status_code": c_res.status_code, "detail": c_res.text}
            continue

        assignment_data = c_res.json()
        asg_id = assignment_data["id"]
        test_record_ids[f"assignment_{atype.lower()}"] = asg_id

        # 2. Candidate Dashboard / Inbox View
        cand_inbox = requests.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        inbox_tasks = parse_items(cand_inbox.json())
        found_in_inbox = any(str(task.get("assignment_id")) == str(asg_id) or str(task.get("id")) == str(asg_id) for task in inbox_tasks)

        # 3. Candidate Start Workflow
        start_res = requests.post(f"{BASE_URL}/candidate/assignments/{asg_id}/start", headers=cand_a_headers)
        start_ok = start_res.status_code == 200 and start_res.json().get("status") == "IN_PROGRESS"

        # 4. Candidate Submit Workflow
        submit_payload = {
            "score": 92.5,
            "submission_ref_id": f"sub-ref-{atype.lower()}-{rand_suffix}",
            "submission_data": {"completed": True, "notes": f"Submitted {atype}"}
        }
        submit_res = requests.post(f"{BASE_URL}/candidate/assignments/{asg_id}/submit", json=submit_payload, headers=cand_a_headers)
        submit_ok = submit_res.status_code == 200 and submit_res.json().get("status") == "COMPLETED" and submit_res.json().get("score") == 92.5

        # 5. Refresh Inbox Persistence Check
        refreshed_inbox = requests.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        ref_tasks = parse_items(refreshed_inbox.json())
        matching_ref = next((t for t in ref_tasks if str(t.get("assignment_id")) == str(asg_id) or str(t.get("id")) == str(asg_id)), None)
        persist_ok = matching_ref is not None and matching_ref.get("status") == "COMPLETED" and matching_ref.get("score") == 92.5

        # 6. Admin Detail & Telemetry Update Check
        adm_detail = requests.get(f"{BASE_URL}/admin/assignments/{asg_id}", headers=admin_headers)
        adm_ok = adm_detail.status_code == 200 and adm_detail.json().get("total_completed") == 1 and adm_detail.json().get("completion_rate") == 100.0

        all_passed = (found_in_inbox and start_ok and submit_ok and persist_ok and adm_ok)

        status_str = "VERIFIED" if all_passed else "PARTIALLY_VERIFIED"
        results_step2[atype] = {
            "status": status_str,
            "assignment_id": asg_id,
            "admin_created": True,
            "inbox_received": found_in_inbox,
            "start_worked": start_ok,
            "submit_worked": submit_ok,
            "score_persisted": persist_ok,
            "admin_telemetry_updated": adm_ok
        }
        print(f"[{status_str}] Type {atype}: AdminCreated=True, InboxReceived={found_in_inbox}, Started={start_ok}, Submitted={submit_ok}, ScorePersisted={persist_ok}, TelemetryUpdated={adm_ok}")

    # ============================================================
    # STEP 3 — VERIFY 8 TARGETING MECHANISMS
    # ============================================================
    print("\n============================================================")
    print("STEP 3: TESTING ALL 8 TARGETING MECHANISMS")
    print("============================================================")

    targeting_tests = [
        ("INDIVIDUAL", {"candidate_id": cand_a_id}, [cand_a_id], [cand_b_id]),
        ("GROUP", {"candidate_ids": [cand_a_id, cand_b_id]}, [cand_a_id, cand_b_id], []),
        ("ROLE", {"role": "CANDIDATE"}, [cand_a_id, cand_b_id], []),
        ("SKILL", {"skill": "python"}, [cand_a_id], []), # Cand A has python skill
        ("SUBSCRIPTION_TIER", {"tier": "FREE"}, [cand_a_id, cand_b_id], []),
        ("COMPANY", {"company_id": str(uuid.uuid4())}, [], [cand_a_id, cand_b_id]),
        ("SEGMENT", {"candidate_ids": [cand_b_id]}, [cand_b_id], [cand_a_id]),
        ("ALL", {}, [cand_a_id, cand_b_id], [])
    ]

    for tname, tfilter, expected_received, expected_blocked in targeting_tests:
        print(f"\n--- Testing Targeting Mechanism: {tname} ---")
        t_payload = {
            "title": f"Targeting Test {tname} {rand_suffix}",
            "description": f"Verification task for targeting {tname}",
            "assignment_type": "QUESTION",
            "priority": "MEDIUM",
            "target_type": tname,
            "target_filter": tfilter
        }

        asg_resp = requests.post(f"{BASE_URL}/admin/assignments", json=t_payload, headers=admin_headers)
        if asg_resp.status_code not in (200, 201):
            results_step3[tname] = {"status": "FAILED", "post_status": asg_resp.status_code, "detail": asg_resp.text}
            continue

        t_asg_id = asg_resp.json()["id"]

        # Check Cand A inbox
        inbox_a = requests.get(f"{BASE_URL}/candidate/assignments", headers=cand_a_headers)
        tasks_a = parse_items(inbox_a.json())
        cand_a_has_it = any(str(t.get("assignment_id")) == str(t_asg_id) for tt in tasks_a for t in [tt])

        # Check Cand B inbox
        inbox_b = requests.get(f"{BASE_URL}/candidate/assignments", headers=cand_b_headers)
        tasks_b = parse_items(inbox_b.json())
        cand_b_has_it = any(str(t.get("assignment_id")) == str(t_asg_id) for tt in tasks_b for t in [tt])

        a_expected = cand_a_id in expected_received
        b_expected = cand_b_id in expected_received

        a_correct = (cand_a_has_it == a_expected)
        b_correct = (cand_b_has_it == b_expected)

        targeting_ok = a_correct and b_correct

        status_str = "VERIFIED" if targeting_ok else "FAILED"
        results_step3[tname] = {
            "status": status_str,
            "assignment_id": t_asg_id,
            "cand_a_expected": a_expected,
            "cand_a_received": cand_a_has_it,
            "cand_b_expected": b_expected,
            "cand_b_received": cand_b_has_it,
            "isolation_correct": targeting_ok
        }
        print(f"[{status_str}] Targeting {tname}: CandA (Expected={a_expected}, Got={cand_a_has_it}), CandB (Expected={b_expected}, Got={cand_b_has_it})")

    output = {
        "step2_assignment_types": results_step2,
        "step3_targeting_mechanisms": results_step3,
        "test_record_ids": test_record_ids
    }

    with open("scratch/step2_step3_verification_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n============================================================")
    print("STEP 2 & STEP 3 VERIFICATION SUMMARY")
    print("============================================================")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run_step2_step3_verification()
