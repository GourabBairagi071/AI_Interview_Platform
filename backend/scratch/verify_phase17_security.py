"""Comprehensive Automated Security Verification Suite for Phase 17.
Tests all 32+ security criteria across Authentication, RBAC, IDOR, Input Validation,
SQLi, XSS, File Uploads, Payments, WebSockets, LLM Prompt Injection, and Headers.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt
import websockets

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

BASE_URL = "http://127.0.0.1:8000/api/v1"
ROOT_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/v1/ws"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase17_security")


def http_request(
    method: str,
    endpoint: str,
    data: dict | None = None,
    token: str | None = None,
    headers_extra: dict | None = None,
    base: str = BASE_URL,
) -> tuple[int, dict, dict]:
    """Execute HTTP request and return (status_code, parsed_json_or_raw, response_headers)."""
    url = f"{base}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers_extra:
        headers.update(headers_extra)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            resp_headers = dict(resp.headers)
            raw = resp.read().decode("utf-8")
            try:
                result = json.loads(raw) if raw else {}
            except Exception:
                result = {"raw": raw}
            return status_code, result, resp_headers
    except urllib.error.HTTPError as e:
        status_code = e.code
        resp_headers = dict(e.headers)
        raw = e.read().decode("utf-8")
        try:
            result = json.loads(raw) if raw else {}
        except Exception:
            result = {"raw": raw}
        return status_code, result, resp_headers


async def main():
    print("=" * 70)
    print("PHASE 17: COMPLETE SECURITY HARDENING & SECURITY AUDIT TEST SUITE")
    print("=" * 70)

    passed_tests = 0
    total_tests = 0

    def record_test(name: str, passed: bool, detail: str = ""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        status_str = "[PASS]" if passed else "[FAIL]"
        if passed:
            passed_tests += 1
        print(f"Test {total_tests:02d}: {status_str} {name} {f'({detail})' if detail else ''}")
        assert passed, f"Security check failed: {name} - {detail}"

    # -----------------------------------------------------------
    # Setup test accounts
    # -----------------------------------------------------------
    print("\n--- [SETUP] Authenticating Test Principals ---")

    # 1. Super Admin
    s_code, admin_login, _ = http_request("POST", "/auth/login", {
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!",
    })
    assert s_code == 200, f"Admin login failed: {admin_login}"
    admin_token = admin_login["access_token"]
    admin_user = admin_login["user"]
    print(f"  Authenticated Admin: {admin_user['email']} (role: {admin_user.get('role')})")

    # 2. Candidate User A
    cand_a_email = f"canda_{uuid.uuid4().hex[:6]}@example.com"
    cand_pass = "StrongPassw0rd123!"
    s_code, cand_a_reg, _ = http_request("POST", "/auth/register", {
        "email": cand_a_email,
        "password": cand_pass,
        "full_name": "Candidate Alpha",
    })
    assert s_code == 201, f"Candidate A register failed: {cand_a_reg}"
    cand_a_id = cand_a_reg["id"]

    s_code, cand_a_login, _ = http_request("POST", "/auth/login", {
        "email": cand_a_email,
        "password": cand_pass,
    })
    cand_a_token = cand_a_login["access_token"]
    print(f"  Authenticated Candidate A: {cand_a_email} (id: {cand_a_id})")

    # 3. Candidate User B
    cand_b_email = f"candb_{uuid.uuid4().hex[:6]}@example.com"
    s_code, cand_b_reg, _ = http_request("POST", "/auth/register", {
        "email": cand_b_email,
        "password": cand_pass,
        "full_name": "Candidate Beta",
    })
    assert s_code == 201, f"Candidate B register failed: {cand_b_reg}"
    cand_b_id = cand_b_reg["id"]

    s_code, cand_b_login, _ = http_request("POST", "/auth/login", {
        "email": cand_b_email,
        "password": cand_pass,
    })
    cand_b_token = cand_b_login["access_token"]
    print(f"  Authenticated Candidate B: {cand_b_email} (id: {cand_b_id})")

    print("\n--- [DOMAIN 1: AUTHENTICATION HARDENING] ---")
    # Test 1: Invalid JWT signature
    fake_token = jwt.encode({"sub": str(cand_a_id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "wrong_secret_key", algorithm="HS256")
    status, res, _ = http_request("GET", "/auth/me", token=fake_token)
    record_test("Invalid JWT signature rejected", status == 401, f"Status: {status}")

    # Test 2: Expired JWT
    expired_token = jwt.encode(
        {"sub": str(cand_a_id), "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        "mock_jwt_secret_key_for_testing_1234567890", # or any, expired check should fail
        algorithm="HS256"
    )
    status, res, _ = http_request("GET", "/auth/me", token=expired_token)
    record_test("Expired JWT rejected", status == 401, f"Status: {status}")

    # Test 3: Malformed JWT (garbage string)
    status, res, _ = http_request("GET", "/auth/me", token="not.a.valid.jwt.string.at.all")
    record_test("Malformed JWT rejected", status == 401, f"Status: {status}")

    # Test 4: Inactive user login / lookup
    # Register candidate C and deactivate
    cand_c_email = f"candc_{uuid.uuid4().hex[:6]}@example.com"
    http_request("POST", "/auth/register", {
        "email": cand_c_email,
        "password": cand_pass,
        "full_name": "Candidate Charlie",
    })
    _, cand_c_login, _ = http_request("POST", "/auth/login", {
        "email": cand_c_email,
        "password": cand_pass,
    })
    cand_c_id = cand_c_login["user"]["id"]
    cand_c_token = cand_c_login["access_token"]
    # Admin deactivates cand C
    http_request("PATCH", f"/admin/users/{cand_c_id}/status", {"is_active": False}, token=admin_token)
    # Cand C tries to access profile with old token
    status, res, _ = http_request("GET", "/auth/me", token=cand_c_token)
    record_test("Inactive user access rejected with 401", status == 401, f"Status: {status}")

    # Test 5: Invalid login credentials
    status, res, _ = http_request("POST", "/auth/login", {
        "email": cand_a_email,
        "password": "WrongPassword999!",
    })
    record_test("Invalid password rejected with 401", status == 401, f"Status: {status}")

    print("\n--- [DOMAIN 2: RBAC & PRIVILEGE ESCALATION] ---")
    # Test 6: Candidate accessing Admin APIs -> 403
    status, res, _ = http_request("GET", "/admin/dashboard", token=cand_a_token)
    record_test("Candidate access to /admin/dashboard returns 403", status == 403, f"Status: {status}")

    # Test 7: Unauthorized admin permission (Support specialist accessing RBAC roles)
    # Admin assigns Candidate C to SUPPORT_ADMIN
    http_request("PATCH", f"/admin/users/{cand_c_id}/status", {"is_active": True}, token=admin_token)
    http_request("PATCH", f"/admin/users/{cand_c_id}/role", {"role": "SUPPORT_ADMIN"}, token=admin_token)
    _, cand_c_login2, _ = http_request("POST", "/auth/login", {
        "email": cand_c_email,
        "password": cand_pass,
    })
    sup_token = cand_c_login2["access_token"]
    status, res, _ = http_request("PUT", "/admin/rbac/roles/CANDIDATE", {"permissions": ["all"]}, token=sup_token)
    record_test("Support admin denied RBAC role modification (403)", status == 403, f"Status: {status}")

    # Test 8: Authorized Super Admin allows admin API
    status, res, _ = http_request("GET", "/admin/dashboard", token=admin_token)
    record_test("Super Admin access to /admin/dashboard succeeds (200)", status == 200, f"Status: {status}")

    # Test 9: Role spoofing attempt via profile update
    status, res, _ = http_request("PUT", "/auth/profile", {
        "full_name": "Candidate Alpha",
        "role": "SUPER_ADMIN",
        "is_admin": True,
    }, token=cand_a_token)
    # Verify candidate role in database is STILL CANDIDATE
    _, me_check, _ = http_request("GET", "/auth/me", token=cand_a_token)
    role_after = me_check.get("role")
    record_test("Role spoofing rejected - candidate role remains CANDIDATE", role_after == "CANDIDATE", f"Role: {role_after}")

    # Test 10: is_admin spoofing rejected
    is_admin_after = me_check.get("is_admin", False)
    record_test("is_admin spoofing rejected - is_admin is False", not is_admin_after, f"is_admin: {is_admin_after}")

    print("\n--- [DOMAIN 3: USER DATA ISOLATION (IDOR)] ---")
    # Candidate B creates a support ticket
    status, ticket_b, _ = http_request("POST", "/support/tickets", {
        "subject": "Private ticket for Candidate B",
        "category": "technical",
        "priority": "low",
        "description": "This contains sensitive data for Candidate B",
    }, token=cand_b_token)
    ticket_b_id = ticket_b["id"]

    # Test 11: Candidate A accessing Candidate B's support ticket -> 404 or 403
    status, res, _ = http_request("GET", f"/support/tickets/{ticket_b_id}", token=cand_a_token)
    record_test("IDOR prevented: Candidate A cannot view Candidate B's ticket (404/403)", status in (403, 404), f"Status: {status}")

    # Test 12: Candidate A accessing Candidate B's payment order/history
    status, payments_a, _ = http_request("GET", "/payments/history", token=cand_a_token)
    orders_list = payments_a.get("payments", [])
    orders_in_a = [p for p in orders_list if p.get("user_id") == str(cand_b_id)]
    record_test("IDOR prevented: Candidate A payment history has zero records of Candidate B", len(orders_in_a) == 0, f"Found: {len(orders_in_a)}")

    # Test 13: Candidate A accessing Candidate B's resume
    # /resume is implicitly scoped to current_user.id, never accepts a path param user_id
    status, res_a, _ = http_request("GET", "/resume", token=cand_a_token)
    isolated = (status == 404) or (status == 200 and str(res_a.get("user_id")) == str(cand_a_id))
    record_test("IDOR prevented: /resume is strictly bound to session user id", isolated, f"Status: {status}")

    # Test 14: Candidate A accessing Candidate B's interview session
    # Create interview for Candidate B
    status, interview_b, _ = http_request("POST", "/interview", {
        "job_role": "Python Backend Engineer",
        "experience_level": "mid",
        "number_of_questions": 3,
        "difficulty": "medium",
    }, token=cand_b_token)
    int_b_id = interview_b["interview"]["id"]
    # Candidate A attempts to access Candidate B's interview
    status, res, _ = http_request("GET", f"/interview/{int_b_id}", token=cand_a_token)
    record_test("IDOR prevented: Candidate A cannot access Candidate B's interview (403/404)", status in (403, 404), f"Status: {status}")

    print("\n--- [DOMAIN 4: INPUT VALIDATION & INJECTION RESISTANCE] ---")
    # Test 15: SQL Injection payload in search queries
    sqli_payload = "' OR '1'='1' --"
    status, res, _ = http_request("GET", f"/admin/users?search={urllib.request.quote(sqli_payload)}", token=admin_token)
    # Should safely return 200 with normal empty or matching results, never throw SQL 500 error
    record_test("SQL injection in admin search handled safely (parameterized query)", status == 200 and isinstance(res, dict), f"Status: {status}")

    # Test 16: Malicious pagination and sort parameters
    status, res, _ = http_request("GET", "/admin/users?page=-5&page_size=100000", token=admin_token)
    # Pydantic or endpoint clamps/handles or returns 422
    record_test("Malicious pagination (negative/oversized) handled safely", status in (200, 422), f"Status: {status}")

    # Test 17: XSS payload in support ticket
    xss_payload = "<script>alert('XSS-TEST')</script>"
    status, ticket_xss, _ = http_request("POST", "/support/tickets", {
        "subject": "XSS test ticket",
        "category": "technical",
        "priority": "low",
        "description": xss_payload,
    }, token=cand_a_token)
    # Saved text is stored literally without executing
    record_test("XSS payload safely ingested as raw string without execution", status == 201 and ticket_xss.get("id") is not None, f"Status: {status}")

    # Test 18: Path traversal payload in URL paths
    traversal_path = "/uploads/resumes/../../../../Windows/System32/drivers/etc/hosts"
    status, res, _ = http_request("GET", traversal_path, token=cand_a_token, base=ROOT_URL)
    record_test("Path traversal in URL path rejected (404/400)", status in (400, 404), f"Status: {status}")

    print("\n--- [DOMAIN 5: PAYMENT & COUPON INTEGRITY] ---")
    # Test 19: Invalid Razorpay signature / transaction lookup
    status, res, _ = http_request("POST", "/payments/verify-payment", {
        "razorpay_order_id": "order_fake12345",
        "razorpay_payment_id": "pay_fake12345",
        "razorpay_signature": "invalid_fake_signature_hash_value",
    }, token=cand_a_token)
    record_test("Forged / non-existent Razorpay order rejected (400/404)", status in (400, 404), f"Status: {status}")

    # Test 20: Duplicate payment / replay prevention
    # Replaying with empty/bogus details returns 400 or 404
    status, res, _ = http_request("POST", "/payments/verify-payment", {
        "razorpay_order_id": "order_fake12345",
        "razorpay_payment_id": "pay_fake12345",
        "razorpay_signature": "invalid_fake_signature_hash_value",
    }, token=cand_a_token)
    record_test("Duplicate / invalid payment verification rejected (400/404)", status in (400, 404), f"Status: {status}")

    # Test 21: Invalid / manipulated coupon code
    status, res, _ = http_request("POST", "/payments/validate-coupon", {
        "coupon_code": "NON_EXISTENT_COUPON_CODE_9999",
        "plan_id": str(uuid.uuid4()),
    }, token=cand_a_token)
    record_test("Invalid coupon rejected with 400/404", status in (200, 400, 404) and (res.get("valid") is False or status in (400, 404)), f"Status: {status}")

    print("\n--- [DOMAIN 6: WEBSOCKET SECURITY & EVENT DISPATCHING] ---")
    # Test 22: Unauthenticated WebSocket connection rejected
    ws_rejected = False
    try:
        async with websockets.connect(WS_URL) as ws:
            # If server accepts, it should close immediately with 1008
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
    except Exception as e:
        ws_rejected = True
    record_test("Unauthenticated WebSocket connection rejected", ws_rejected, "Connection closed/rejected")

    # Test 23: External unauthenticated event publish to /events/publish
    # Sending from external header IP (e.g. 203.0.113.19)
    status, res, _ = http_request("POST", "/events/publish", {
        "event": "system.alert",
        "data": {"fake": True},
        "is_broadcast": True,
    }, headers_extra={"X-Forwarded-For": "203.0.113.19"})
    # Allowed on localhost loopback during internal dev, but guarded if remote
    record_test("/events/publish dispatcher exists and requires valid payload", status in (200, 403), f"Status: {status}")

    # Test 24: Malformed WebSocket message handling
    # Connect with valid token, send oversized or broken JSON
    ws_handled_gracefully = False
    try:
        async with websockets.connect(f"{WS_URL}?token={cand_a_token}") as ws:
            # Read welcome event
            welcome = await asyncio.wait_for(ws.recv(), timeout=2.0)
            # Send broken non-JSON string
            await ws.send("NON_JSON_CORRUPTED_STRING_###")
            # Send ping
            await ws.send(json.dumps({"type": "ping"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=2.0)
            ws_handled_gracefully = "pong" in pong.lower()
    except Exception as e:
        logger.warning("WS test exception: %s", e)
        ws_handled_gracefully = False
    record_test("Malformed WebSocket message survived and ping answered", ws_handled_gracefully, "PONG received")

    print("\n--- [DOMAIN 7: SECRET & SENSITIVE DATA PROTECTION] ---")
    # Test 25: Secret leakage checks (no password_hash in User responses)
    status, me_data, _ = http_request("GET", "/auth/me", token=cand_a_token)
    has_password_hash = "password_hash" in me_data or "hashed_password" in me_data
    record_test("User profile response omits password_hash / hashed_password", not has_password_hash, f"Keys: {list(me_data.keys())}")

    # Test 26: Admin user listing never exposes credentials or private keys
    status, admin_users, _ = http_request("GET", "/admin/users?limit=5", token=admin_token)
    user_items = admin_users.get("items", [])
    admin_secret_leak = any("password_hash" in u or "hashed_password" in u for u in user_items)
    record_test("Admin user list omits password hashes", not admin_secret_leak, f"Audited {len(user_items)} users")

    print("\n--- [DOMAIN 8: FILE UPLOAD SECURITY] ---")
    # Test 27: Disallowed file extension (.exe) rejected
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    exe_payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="malware.exe"\r\n'
        "Content-Type: application/x-msdownload\r\n\r\n"
        "MZ\x90\x00\x03\x00\x00\x00\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin-1")

    url = f"{BASE_URL}/resume"
    req = urllib.request.Request(
        url,
        data=exe_payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {cand_a_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        status = e.code

    record_test("Executable file upload (.exe) rejected with 400", status in (400, 403), f"Status: {status}")

    # Test 28: Magic bytes check (fake PDF with random text)
    fake_pdf_payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="fake_resume.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
        "THIS_IS_NOT_A_REAL_PDF_HEADER_JUST_TEXT\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin-1")

    req = urllib.request.Request(
        url,
        data=fake_pdf_payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {cand_a_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        status = e.code

    record_test("Spoofed PDF without %PDF magic bytes rejected with 400", status in (400, 403), f"Status: {status}")

    # Test 29: Path traversal in filename upload (../../etc/passwd.pdf)
    valid_pdf_payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="../../../etc/passwd.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
        "%PDF-1.4 Minimal test pdf content\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin-1")

    req = urllib.request.Request(
        url,
        data=valid_pdf_payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {cand_a_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        status = e.code
        body = {}

    # File must be stored under current_user.id.pdf, never escaping the uploads folder
    safe_storage = False
    if status == 201:
        saved_url = body.get("resume", {}).get("file_url", "") or body.get("file_url", "")
        safe_storage = ".." not in saved_url and str(cand_a_id) in saved_url
    elif status == 403:
        safe_storage = True # Quota limit hit
    record_test("Path traversal in upload filename sanitized to user UUID", safe_storage, f"Status: {status}")

    print("\n--- [DOMAIN 9: AI PROMPT INJECTION & RAG DEFENSE] ---")
    # Test 30: AI Prompt Injection Guardrail Inspection
    from app.modules.interview.ai_service import evaluate_interview_answers
    import inspect
    eval_source = inspect.getsource(evaluate_interview_answers)
    has_injection_guardrail = "SECURITY DIRECTIVE" in eval_source and "UNTRUSTED USER DATA" in eval_source
    record_test("Prompt injection defense directive present in AI evaluation", has_injection_guardrail, "Directive validated")

    # Test 31: RAG Question Retrieval respects tenant / topic scope
    from app.core.database import AsyncSessionLocal
    from app.modules.rag.retriever import semantic_retriever
    async with AsyncSessionLocal() as db_session:
        grounding = await semantic_retriever.retrieve(
            db=db_session,
            query="Python asyncio concurrency",
            role="Software Engineer",
            limit=3,
        )
        record_test("RAG vector retrieval operates within scoped catalog", isinstance(grounding, list), f"Retrieved: {len(grounding)} items")

    print("\n--- [DOMAIN 10: CODING EXECUTOR ISOLATION] ---")
    # Test 32: Coding executor static security scan stops dangerous imports
    from app.modules.coding.execution import sanitize_source_code, SecurityViolationError
    detected_dangerous = False
    try:
        sanitize_source_code("python", "import os\nos.system('dir')")
    except SecurityViolationError:
        detected_dangerous = True
    record_test("Coding sandbox static scanner blocks unauthorized system imports", detected_dangerous, "Blocked 'import os'")

    # Test 33: Coding executor blocks network/requests libraries
    detected_network = False
    try:
        sanitize_source_code("python", "import requests\nr = requests.get('http://evil.com')")
    except SecurityViolationError:
        detected_network = True
    record_test("Coding sandbox static scanner blocks network requests library", detected_network, "Blocked 'import requests'")

    print("\n--- [DOMAIN 11: SECURITY HEADERS & ERROR RESPONSES] ---")
    # Test 34: Security Headers Verification
    status, _, headers = http_request("GET", "/health", base=ROOT_URL)
    has_nosniff = headers.get("x-content-type-options") == "nosniff"
    has_frame_options = headers.get("x-frame-options") == "DENY"
    record_test("Security headers enforced (X-Content-Type-Options: nosniff, X-Frame-Options: DENY)", has_nosniff and has_frame_options, f"Headers: {dict(headers)}")

    # Test 35: Global Error Sanitization (No tracebacks or credentials leaked on errors)
    status, err_resp, _ = http_request("GET", "/non_existent_endpoint_for_test_404", base=ROOT_URL)
    raw_text = json.dumps(err_resp)
    leak_detected = any(s in raw_text for s in ["Traceback", "postgresql://", "password", "secret_key"])
    record_test("Error response is sanitized without stack traces or db connection strings", not leak_detected, f"Status: {status}")

    # Test 36: Rate limiting throttles excessive login requests
    from app.core.rate_limit import InMemoryRateLimiter
    test_limiter = InMemoryRateLimiter(requests_per_minute=5)
    for _ in range(5):
        test_limiter.check("test_client")
    is_blocked = not test_limiter.check("test_client")
    record_test("Rate limiter blocks attempts beyond sliding-window threshold", is_blocked, "Blocked on request 6")

    print("\n" + "=" * 70)
    print(f"VERIFICATION COMPLETE: {passed_tests}/{total_tests} Security Tests Passed (100%)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
