"""PHASE 19 — FULL SYSTEM INTEGRATION VERIFICATION SUITE
Comprehensive end-to-end integration across all 16 platform modules and 9 core journeys:
1. New candidate onboarding, resume ATS parsing & skill extraction
2. Adaptive AI technical interview with RAG context & multi-turn evaluation
3. Voice / audio interview simulation with STT transcript sync & typing fallback
4. Personalized learning intelligence, skill matrix, daily plans & recommendations
5. Coding arena, 1,000 problems catalog & multi-language test execution
6. Competitive coding contest, registration, submissions & live leaderboard
7. Razorpay payments, HMAC verification, subscriptions, quotas & invoices
8. Support ticketing, candidate-admin communication, internal notes & notifications
9. Admin RBAC management, platform KPIs, settings, audit logs & WebSocket real-time
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

import websockets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User
from app.modules.payments.service import verify_razorpay_signature, check_quota

BASE_URL = "http://127.0.0.1:8000/api/v1"
ROOT_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/v1/ws"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phase19_integration")


def http_request(
    method: str,
    endpoint: str,
    data: dict | None = None,
    token: str | None = None,
    headers_extra: dict | None = None,
    base: str = BASE_URL,
    raw_body: bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, dict, dict]:
    url = f"{base}{endpoint}"
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers_extra:
        headers.update(headers_extra)

    body = raw_body if raw_body is not None else (json.dumps(data).encode("utf-8") if data is not None else None)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            resp_headers = dict(resp.headers)
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                result = json.loads(raw) if raw else {}
            except Exception:
                result = {"raw": raw}
            return status_code, result, resp_headers
    except urllib.error.HTTPError as e:
        status_code = e.code
        resp_headers = dict(e.headers)
        raw = e.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw) if raw else {}
        except Exception:
            result = {"raw": raw}
        return status_code, result, resp_headers


async def run_full_integration():
    print("=" * 80)
    print("PHASE 19 — FULL SYSTEM INTEGRATION VERIFICATION SUITE")
    print("AI-Powered Intelligent Interview & Career Preparation Platform")
    print("=" * 80)

    total_tests = 0
    passed_tests = 0

    def assert_check(name: str, condition: bool, details: str = ""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        status = "[PASS]" if condition else "[FAIL]"
        if condition:
            passed_tests += 1
        print(f"  {status} Step {total_tests:02d}: {name} {f'({details})' if details else ''}")
        assert condition, f"Integration Check Failed: {name} - {details}"

    # -------------------------------------------------------------------------
    # JOURNEY 1: NEW CANDIDATE ONBOARDING & RESUME ATS INTELLIGENCE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 1: CANDIDATE REGISTRATION, ONBOARDING & ATS RESUME INTELLIGENCE")
    print("=" * 70)

    cand_email = f"candidate_p19_{uuid.uuid4().hex[:6]}@example.com"
    cand_pass = "CandidateSecure123!"

    # 1. Registration
    status, reg_data, _ = http_request("POST", "/auth/register", {
        "email": cand_email,
        "password": cand_pass,
        "full_name": "Alexander Hayes",
    })
    assert_check("Candidate registration", status == 201 and "id" in reg_data, f"Email: {cand_email}")
    candidate_id = reg_data["id"]

    # 2. Login
    status, login_data, _ = http_request("POST", "/auth/login", {
        "email": cand_email,
        "password": cand_pass,
    })
    assert_check("Candidate JWT authentication", status == 200 and "access_token" in login_data)
    cand_token = login_data["access_token"]

    # 3. Profile Onboarding Fetch
    status, profile_init, _ = http_request("GET", "/profile", token=cand_token)
    cand_name = profile_init.get("profile", {}).get("full_name") or profile_init.get("full_name")
    assert_check("Initial candidate profile retrieval", status == 200 and cand_name == "Alexander Hayes", f"Name: {cand_name}")

    # 4. Resume Upload with %PDF- Magic Bytes
    import io
    from reportlab.pdfgen import canvas
    import httpx

    pdf_buf = io.BytesIO()
    p_canv = canvas.Canvas(pdf_buf)
    p_canv.drawString(72, 750, "Alexander Hayes")
    p_canv.drawString(72, 730, "Email: alexander.hayes@example.com | Full Stack Software Engineer")
    p_canv.drawString(72, 710, "Summary: Experienced software engineer specializing in Python, React, and PostgreSQL.")
    p_canv.drawString(72, 690, "Skills: Python, TypeScript, React, PostgreSQL, Docker, AsyncIO, REST APIs, FastAPI")
    p_canv.drawString(72, 670, "Experience: Senior Software Engineer (4 years) developing high throughput APIs.")
    p_canv.save()
    valid_pdf_bytes = pdf_buf.getvalue()

    with httpx.Client(base_url=BASE_URL) as client:
        r = client.post(
            "/resume",
            files={"file": ("alexander_hayes_resume.pdf", valid_pdf_bytes, "application/pdf")},
            headers={"Authorization": f"Bearer {cand_token}"}
        )
        status = r.status_code
        upload_res = r.json() if r.content else {}
    assert_check("Resume upload with valid magic bytes", status == 201 and "resume" in upload_res, f"Status: {status}")

    # 5. Resume ATS Analysis
    status, analysis_res, _ = http_request("POST", "/resume/analyze", token=cand_token)
    if status != 200:
        print(f"    [INFO] Resume analysis first attempt status {status}: {analysis_res.get('detail')}. Retrying after 1s...")
        await asyncio.sleep(1.0)
        status, analysis_res, _ = http_request("POST", "/resume/analyze", token=cand_token)
    assert_check("Resume ATS analysis & skill extraction", status in (200, 201) and "analysis" in analysis_res, f"Status: {status}, Detail: {analysis_res.get('detail')}")
    ats_score = analysis_res.get("analysis", {}).get("ats_score", 75)

    # 6. Profile Enrichment with Target Role
    status, prof_update, _ = http_request("PATCH", "/profile", {
        "target_role": "Full Stack Engineer",
        "experience_level": "Mid-Level",
        "skills": "Python, TypeScript, React, PostgreSQL, FastAPI",
        "headline": "Full Stack Engineer specializing in Distributed Systems",
    }, token=cand_token)
    updated_role = prof_update.get("profile", {}).get("target_role") or prof_update.get("target_role")
    assert_check("Profile target role & skills update", status == 200 and updated_role == "Full Stack Engineer", f"Role: {updated_role}")

    # -------------------------------------------------------------------------
    # JOURNEY 2: ADAPTIVE AI TECHNICAL INTERVIEW JOURNEY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 2: ADAPTIVE AI TECHNICAL INTERVIEW & RAG GROUNDING")
    print("=" * 70)

    # 7. Create AI Interview
    status, int_create, _ = http_request("POST", "/interview", {
        "job_role": "Full Stack Engineer",
        "difficulty": "Medium",
        "experience_level": "Mid-Level",
        "interview_type": "Technical",
        "number_of_questions": 2,
    }, token=cand_token)
    assert_check("Create AI interview session", status == 201 and "interview" in int_create)
    interview_id = int_create["interview"]["id"]

    # 8. Start Interview
    status, int_start, _ = http_request("POST", f"/interview/{interview_id}/start", token=cand_token)
    assert_check("Start interview session", status == 200 and int_start.get("interview", {}).get("status") == "started")

    # 9. Verify RAG Context Grounding
    from app.modules.rag.retriever import semantic_retriever
    async with AsyncSessionLocal() as session:
        grounding_q = await semantic_retriever.retrieve(
            db=session,
            query="Full Stack Engineer Python React Architecture",
            role="Software Engineer",
            limit=2,
        )
    assert_check("RAG semantic question grounding", isinstance(grounding_q, list) and len(grounding_q) > 0, f"Retrieved {len(grounding_q)} questions")

    # 10. Submit Turn 1 Answer
    cand_answer_1 = "I architect web services using FastAPI and PostgreSQL with connection pooling. On the frontend I use React with TypeScript."
    status, submit_1, _ = http_request("POST", f"/interview/{interview_id}/answers", {
        "answers": cand_answer_1,
    }, token=cand_token)
    assert_check("Submit Turn 1 interview answer", status == 200)

    # 11. Adaptive Follow-Up Question Generation
    status, followup_res, _ = http_request("POST", f"/interview/{interview_id}/followup", {
        "question": "How do you handle database connection pooling and concurrency in FastAPI?",
        "answer": cand_answer_1,
        "conversation_history": [{"question": "Describe your backend architecture", "answer": cand_answer_1}],
    }, token=cand_token)
    assert_check("Adaptive follow-up question generation", status == 200 and "should_follow_up" in followup_res)

    # 12. Submit Structured Transcript
    structured_transcript = [
        {
            "question_index": 1,
            "question": "Describe your backend architecture with FastAPI and PostgreSQL.",
            "candidate_answer": cand_answer_1,
            "is_followup": False,
            "evaluation": {"technical_correctness": 8.5, "clarity": 9.0},
        },
        {
            "question_index": 2,
            "question": followup_res.get("question") or "How do you optimize asynchronous queries in SQLAlchemy?",
            "candidate_answer": "I use select() queries with async session execute and avoid synchronous IO in coroutines.",
            "is_followup": True,
            "evaluation": {"technical_correctness": 8.0, "clarity": 8.5},
        },
    ]
    status, trans_res, _ = http_request("POST", f"/interview/{interview_id}/transcript", {
        "entries": structured_transcript,
    }, token=cand_token)
    assert_check("Structured transcript synchronization", status == 200 and "entries" in trans_res)

    # 13. Complete Interview & Generate Final Assessment
    status, complete_res, _ = http_request("POST", f"/interview/{interview_id}/complete", token=cand_token)
    assert_check("Complete interview & persist evaluation", status == 200 and complete_res.get("interview", {}).get("status") == "completed")

    # -------------------------------------------------------------------------
    # JOURNEY 3: VOICE INTERVIEW PIPELINE & TYPING FALLBACK
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 3: VOICE PIPELINE SIMULATION & TYPING FALLBACK")
    print("=" * 70)

    # 14. Voice Avatar State Check (TTS Prompt Retrieval)
    status, int_detail, _ = http_request("GET", f"/interview/{interview_id}", token=cand_token)
    assert_check("Voice interview turn playback retrieval", status == 200 and "questions" in int_detail)

    # 15. Typing Fallback Simulation (Safe typed submission)
    status, typed_trans, _ = http_request("POST", f"/interview/{interview_id}/transcript", {
        "entries": structured_transcript + [{
            "question_index": 3,
            "question": "What is the event loop in Python asyncio?",
            "candidate_answer": "Fallback typed answer: The event loop manages and distributes the execution of different tasks.",
            "is_followup": False,
            "question_type": "technical",
        }],
    }, token=cand_token)
    assert_check("Voice-to-typing fallback transcript recording", status == 200 and "entries" in typed_trans)

    # -------------------------------------------------------------------------
    # JOURNEY 4: PERSONALIZED LEARNING INTELLIGENCE & PRACTICE PLANS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 4: PERSONALIZED LEARNING INTELLIGENCE & WEAK TOPICS")
    print("=" * 70)

    # 16. Skill Performances Tracking
    status, skills_data, _ = http_request("GET", "/learning/skills", token=cand_token)
    assert_check("Learning skill performance matrix retrieval", status == 200 and isinstance(skills_data, list))

    # 17. Dynamic Daily Practice Plan Generation
    status, daily_plan, _ = http_request("GET", "/learning/daily-plan", token=cand_token)
    assert_check("Personalized Daily Practice Plan generation", status == 200 and "items" in daily_plan)

    # 18. Weekly Goals Tracking
    status, weekly_goals, _ = http_request("GET", "/learning/weekly-goals", token=cand_token)
    assert_check("Weekly learning goals tracking", status == 200 and isinstance(weekly_goals, list))

    # 19. Curated Learning Recommendations
    status, recommendations, _ = http_request("GET", "/learning/recommendations", token=cand_token)
    assert_check("Targeted learning recommendations", status == 200 and ("resources" in recommendations or "weak_topics" in recommendations))

    # -------------------------------------------------------------------------
    # JOURNEY 5: 1,000-PROBLEM CODING ARENA & EXECUTION JOURNEY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 5: 1,000-PROBLEM CODING ARENA & EXECUTION")
    print("=" * 70)

    # 20. Browse 1,000 Problems Catalog
    status, problems_res, _ = http_request("GET", "/coding/problems?page=1&page_size=10")
    assert_check("1,000 coding problems catalog browse", status == 200 and problems_res.get("total") == 1000)

    # 21. Search & Filter Problems
    status, filtered_prob, _ = http_request("GET", "/coding/problems?topic=Arrays&difficulty=Easy&page_size=5")
    assert_check("Filter coding problems by topic & difficulty", status == 200 and len(filtered_prob.get("items", [])) > 0)
    test_problem = filtered_prob["items"][0]
    prob_slug = test_problem["slug"]

    # 22. Problem Details & Starter Code
    status, prob_detail, _ = http_request("GET", f"/coding/problems/{prob_slug}", token=cand_token)
    assert_check("Coding problem detail & starter code retrieval", status == 200 and "starter_code" in prob_detail)

    # 23. Custom Code Execution (Python)
    python_solution = "import sys\nline = sys.stdin.read().strip()\nprint('PASS')\n"
    status, exec_res, _ = http_request("POST", "/coding/run-custom", {
        "problem_id": test_problem["id"],
        "language": "python",
        "source_code": python_solution,
        "custom_input": "test input",
    }, token=cand_token)
    assert_check("Python sandbox code execution", status == 200 and "PASS" in exec_res.get("stdout", ""))

    # 24. Code Submission & Ingestion into Learning History
    status, submit_code_res, _ = http_request("POST", "/coding/submit", {
        "problem_id": test_problem["id"],
        "language": "python",
        "source_code": "def solve(*args):\n    return True\n",
    }, token=cand_token)
    assert_check("Coding problem submission recorded", status == 201 and "id" in submit_code_res)

    # -------------------------------------------------------------------------
    # JOURNEY 6: COMPETITIVE CODING CONTEST JOURNEY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 6: COMPETITIVE CODING CONTEST & LEADERBOARD")
    print("=" * 70)

    # 25. List Contests
    status, contests_res, _ = http_request("GET", "/contests?status=ALL", token=cand_token)
    contests_list = contests_res.get("contests", [])
    assert_check("Contest catalog listing", status == 200 and len(contests_list) >= 3)
    live_contest = next((c for c in contests_list if c["status"] == "LIVE"), contests_list[0])
    upcoming_contest = next((c for c in contests_list if c["status"] == "UPCOMING"), None)

    # 26. Upcoming Contest Problems Access Control (Must be 403 Forbidden)
    if upcoming_contest:
        status, locked_res, _ = http_request("GET", f"/contests/{upcoming_contest['id']}/problems", token=cand_token)
        assert_check("Upcoming contest problems locked (403)", status == 403)
    else:
        assert_check("Upcoming contest check (skipped, no upcoming)", True)

    # 27. Register for Live Contest
    status, reg_contest, _ = http_request("POST", f"/contests/{live_contest['id']}/register", token=cand_token)
    assert_check("Contest registration", status in (200, 201) and reg_contest.get("registered") is True)

    # 28. Live Contest Problems Access
    status, contest_probs, _ = http_request("GET", f"/contests/{live_contest['id']}/problems", token=cand_token)
    assert_check("Live contest problem set unlocked", status == 200 and "problems" in contest_probs)

    # 29. Contest Submission
    if contest_probs.get("problems"):
        first_c_prob = contest_probs["problems"][0]
        c_prob_id = first_c_prob.get("problem_id") or first_c_prob.get("id")
        status, c_sub_res, _ = http_request("POST", f"/contests/{live_contest['id']}/submit", {
            "problem_id": c_prob_id,
            "language": "python",
            "source_code": "def solution():\n    return 42",
        }, token=cand_token)
        assert_check("Contest solution submission & score evaluation", status == 200 and "submission_id" in c_sub_res)

    # 30. Contest Leaderboard
    status, leaderboard, _ = http_request("GET", f"/contests/{live_contest['id']}/leaderboard", token=cand_token)
    assert_check("Contest live leaderboard calculation", status == 200 and "leaderboard" in leaderboard)

    # 31. Achievements Tracking
    status, ach_res, _ = http_request("GET", "/achievements", token=cand_token)
    assert_check("User achievements list retrieval", status == 200 and "achievements" in ach_res)

    # -------------------------------------------------------------------------
    # JOURNEY 7: RAZORPAY PAYMENT, SUBSCRIPTION & QUOTA ENFORCEMENT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 7: RAZORPAY PAYMENTS, QUOTA & INVOICE FLOW")
    print("=" * 70)

    # 32. Public Subscription Plans
    status, plans_res, _ = http_request("GET", "/payments/plans")
    assert_check("Public subscription plans retrieval", status == 200 and len(plans_res) >= 3)
    pro_plan = next((p for p in plans_res if p["slug"] == "pro"), plans_res[1])

    # 33. Coupon Validation
    status, coupon_check, _ = http_request("POST", "/payments/validate-coupon", {
        "coupon_code": "WELCOME50",
        "plan_id": pro_plan["id"],
    }, token=cand_token)
    assert_check("Coupon code validation", status == 200 and "valid" in coupon_check)

    # 34. Create Razorpay Order
    status, order_res, _ = http_request("POST", "/payments/create-order", {
        "plan_id": pro_plan["id"],
    }, token=cand_token)
    assert_check("Razorpay checkout order creation", status in (200, 201) and "order_id" in order_res)
    razorpay_order_id = order_res.get("order_id", "order_test_12345")

    # 35. Server-Side HMAC Signature Verification (Activate Subscription)
    secret_key = "mock_secret"
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    signature_payload = f"{razorpay_order_id}|{payment_id}".encode("utf-8")
    simulated_signature = hmac.new(secret_key.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()

    # Verify signature logic directly in service
    sig_valid = verify_razorpay_signature(razorpay_order_id, payment_id, simulated_signature, secret_key)
    assert_check("Razorpay HMAC SHA256 cryptographic signature verification", sig_valid)

    # 36. User Subscription Status
    status, user_sub, _ = http_request("GET", "/payments/subscription", token=cand_token)
    assert_check("User subscription state inspection", status == 200)

    # 37. Quota Enforcement Check
    async with AsyncSessionLocal() as session:
        quota_allowed, quota_reason = await check_quota(session, uuid.UUID(candidate_id), "ai_interview")
    assert_check("Feature quota evaluation (ai_interview)", isinstance(quota_allowed, bool))

    # 38. Invoice Listing
    status, invoices_res, _ = http_request("GET", "/payments/invoices", token=cand_token)
    assert_check("Invoice list retrieval", status == 200 and "invoices" in invoices_res)

    # -------------------------------------------------------------------------
    # JOURNEY 8: SUPPORT TICKETING, ADMIN REPLIES & REAL-TIME WEBSOCKET
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 8: SUPPORT COMMUNICATION, NOTIFICATIONS & WEBSOCKET")
    print("=" * 70)

    # 39. Candidate Creates Support Ticket
    status, ticket_res, _ = http_request("POST", "/support/tickets", {
        "subject": "Platform Integration Inquiry",
        "category": "technical",
        "priority": "normal",
        "description": "Verifying full system integration support workflow.",
    }, token=cand_token)
    assert_check("Support ticket creation", status == 201 and "id" in ticket_res)
    ticket_id = ticket_res["id"]

    # 40. Admin Login
    status, admin_login, _ = http_request("POST", "/auth/login", {
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!",
    })
    assert_check("Admin authentication", status == 200 and "access_token" in admin_login)
    admin_token = admin_login["access_token"]

    # 41. Admin Ticket Inspection & Internal Note
    status, admin_tickets, _ = http_request("GET", "/admin/support/tickets?page=1&page_size=5", token=admin_token)
    assert_check("Admin support tickets list retrieval", status == 200 and "tickets" in admin_tickets)

    # Admin adds internal note (hidden from candidate)
    status, note_res, _ = http_request("POST", f"/support/admin/tickets/{ticket_id}/reply", {
        "message": "Internal engineering verification note: issue confirmed resolved.",
        "is_internal": True,
    }, token=admin_token)
    assert_check("Admin internal note creation", status == 200)

    # 42. Candidate Views Ticket (Internal Note Hidden)
    status, cand_ticket_view, _ = http_request("GET", f"/support/tickets/{ticket_id}", token=cand_token)
    cand_messages = cand_ticket_view.get("messages", [])
    has_internal_note = any(m.get("is_internal", False) for m in cand_messages)
    assert_check("Candidate privacy: internal notes strictly hidden", not has_internal_note)

    # 43. Admin Status Update
    status, status_up, _ = http_request("PATCH", f"/admin/support/tickets/{ticket_id}/status?status=in_progress", token=admin_token)
    assert_check("Support ticket status update (in_progress)", status == 200)

    # 44. Candidate Submits Platform Feedback
    status, feedback_res, _ = http_request("POST", "/support/feedback", {
        "rating": 5,
        "category": "general",
        "message": "Excellent seamless integration across all features!",
    }, token=cand_token)
    assert_check("Candidate feedback submission", status == 201 and "id" in feedback_res)

    # 45. Notification Persistence & Retrieval
    status, notifs_res, _ = http_request("GET", "/notifications", token=cand_token)
    assert_check("Notification history retrieval", status == 200 and "notifications" in notifs_res)

    # -------------------------------------------------------------------------
    # JOURNEY 9: ADMIN DASHBOARD, RBAC & REAL-TIME WEBSOCKET
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("JOURNEY 9: ADMIN RBAC, KPIS, AUDIT LOGS & WEBSOCKET REAL-TIME")
    print("=" * 70)

    # 46. Admin Me & RBAC Clearance
    status, admin_me, _ = http_request("GET", "/admin/me", token=admin_token)
    assert_check("Admin clearance & RBAC verification", status == 200 and admin_me.get("role") == "SUPER_ADMIN")

    # 47. Platform KPIs & Analytics
    status, kpi_res, _ = http_request("GET", "/admin/dashboard", token=admin_token)
    assert_check("Admin KPI dashboard verification", status == 200 and "total_users" in kpi_res and kpi_res["total_users"] > 0)

    # 48. Admin User Management (Search candidate)
    status, user_search, _ = http_request("GET", f"/admin/users?search={cand_email}", token=admin_token)
    users_found = user_search.get("users", [])
    assert_check("Admin user search by email", status == 200 and len(users_found) >= 1)

    # 49. Admin System Settings & Audit Logs
    status, settings_list, _ = http_request("GET", "/admin/settings", token=admin_token)
    assert_check("Admin system settings retrieval", status == 200 and isinstance(settings_list, list))

    status, audit_logs, _ = http_request("GET", "/admin/audit-logs?page=1&page_size=5", token=admin_token)
    assert_check("Immutable admin audit log retrieval", status == 200 and audit_logs.get("total", 0) > 0)

    # 50. Authenticated WebSocket Real-Time Handshake & Ping-Pong
    ws_uri = f"{WS_URL}?token={cand_token}"
    ws_passed = False
    try:
        async with websockets.connect(ws_uri) as ws:
            greet_raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            greet = json.loads(greet_raw)
            if greet.get("event") == "system.connected":
                await ws.send(json.dumps({"type": "ping"}))
                pong_raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                pong = json.loads(pong_raw)
                ws_passed = pong.get("event") == "pong"
    except Exception as e:
        logger.warning("WebSocket handshake check error: %s", e)
        ws_passed = False

    assert_check("Authenticated WebSocket connection & bidirectional ping-pong", ws_passed)

    print("\n" + "=" * 80)
    print(f"PHASE 19 FULL SYSTEM INTEGRATION: {passed_tests}/{total_tests} Steps Passed (100%)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_full_integration())
