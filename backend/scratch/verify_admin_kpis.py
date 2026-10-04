"""Automated verification script for Admin Dashboard KPI accuracy and database cross-checking.
Independently queries PostgreSQL via SQLAlchemy and verifies against GET /api/v1/admin/dashboard.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error
import sys

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)

from sqlalchemy import select, func, and_, or_, cast, Date

from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from app.modules.interview.model import Interview
from app.modules.resume.model import Resume
from app.modules.learning.model import LearningProfile
from app.modules.payments.model import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.modules.support.model import SupportTicket
from app.modules.practice.model import PracticeQuestion
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.coding.contest_model import Contest, ContestRegistration
from app.modules.rag.model import InterviewQuestionVector

BASE_URL = "http://127.0.0.1:8000/api/v1"

logging.basicConfig(level=logging.WARNING)


def http_request(method: str, endpoint: str, data: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8")
            return code, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, json.loads(raw) if raw else {}


async def main():
    print("=" * 70)
    print("PHASE 13: ADMIN DASHBOARD KPI ACCURACY & ANALYTICS AUDIT")
    print("=" * 70)

    # 1. Authenticate as Super Admin
    print("\n[Step 1] Authenticating Super Admin via /auth/login...")
    code, auth_data = http_request("POST", "/auth/login", {
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!"
    })
    assert code == 200 and "access_token" in auth_data, f"Super Admin login failed: {auth_data}"
    token = auth_data["access_token"]
    print("[PASS] Super Admin authenticated.")

    # 2. Fetch Dashboard API response
    print("\n[Step 2] Fetching Dashboard API response (/admin/dashboard?time_range=30d)...")
    code, api_data = http_request("GET", "/admin/dashboard?time_range=30d", token=token)
    assert code == 200, f"Dashboard API request failed with status {code}: {api_data}"
    print("[PASS] Dashboard response received.")

    # 3. Direct independent PostgreSQL audit
    print("\n[Step 3] Querying PostgreSQL directly for authoritative baseline...")
    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=30)
    since_7d = now - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        # User counts
        db_total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        db_active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
        db_new_users_30d = (await db.execute(select(func.count(User.id)).where(User.created_at >= since_30d))).scalar() or 0

        # Interview counts & score
        db_total_interviews = (await db.execute(select(func.count(Interview.id)))).scalar() or 0
        db_completed_interviews = (await db.execute(select(func.count(Interview.id)).where(Interview.status == "completed"))).scalar() or 0
        raw_avg_score = (await db.execute(
            select(func.avg(Interview.score)).where(and_(Interview.status == "completed", Interview.score.isnot(None)))
        )).scalar()
        db_avg_interview_score = round(float(raw_avg_score), 2) if raw_avg_score is not None else None

        # ATS Score calculation
        resumes = (await db.execute(select(Resume))).scalars().all()
        ats_scores = []
        for r in resumes:
            if not r.file_url:
                continue
            clean_url = r.file_url.lstrip("/").replace("\\", "/")
            for base in [Path("."), Path(".."), Path("backend")]:
                cand = base / clean_url
                analysis_path = cand.with_suffix(".analysis.json")
                if analysis_path.exists():
                    try:
                        data = json.loads(analysis_path.read_text(encoding="utf-8"))
                        s = data.get("ats_score") if data.get("ats_score") is not None else data.get("estimated_ats_score")
                        if s is not None:
                            ats_scores.append(float(s))
                    except Exception:
                        pass
                    break
        raw_learning_ats = (await db.execute(
            select(func.avg(LearningProfile.overall_readiness_score)).where(LearningProfile.overall_readiness_score.isnot(None))
        )).scalar()
        if ats_scores:
            db_avg_ats_score = round(sum(ats_scores) / len(ats_scores), 2)
        elif raw_learning_ats is not None:
            db_avg_ats_score = round(float(raw_learning_ats), 2)
        else:
            db_avg_ats_score = None

        # Subscriptions
        db_total_plans = (await db.execute(select(func.count(SubscriptionPlan.id)))).scalar() or 0
        db_active_subs = (await db.execute(select(func.count(UserSubscription.id)).where(
            and_(UserSubscription.status == "active", or_(UserSubscription.expires_at == None, UserSubscription.expires_at > now))
        ))).scalar() or 0
        db_expired_subs = (await db.execute(select(func.count(UserSubscription.id)).where(
            or_(UserSubscription.status == "expired", and_(UserSubscription.status == "active", UserSubscription.expires_at.isnot(None), UserSubscription.expires_at <= now))
        ))).scalar() or 0

        # Payments & Revenue
        db_total_payments = (await db.execute(select(func.count(PaymentTransaction.id)))).scalar() or 0
        db_successful_payments = (await db.execute(select(func.count(PaymentTransaction.id)).where(PaymentTransaction.status == "paid"))).scalar() or 0
        db_failed_payments = (await db.execute(select(func.count(PaymentTransaction.id)).where(PaymentTransaction.status == "failed"))).scalar() or 0
        raw_rev = (await db.execute(select(func.sum(PaymentTransaction.amount)).where(PaymentTransaction.status == "paid"))).scalar()
        db_revenue_inr = round(float(raw_rev) / 100.0, 2) if raw_rev else 0.0

        # Support Tickets
        db_total_tickets = (await db.execute(select(func.count(SupportTicket.id)))).scalar() or 0
        db_open_tickets = (await db.execute(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open"))).scalar() or 0
        db_in_prog_tickets = (await db.execute(select(func.count(SupportTicket.id)).where(SupportTicket.status == "in_progress"))).scalar() or 0
        db_pending_tickets = (await db.execute(select(func.count(SupportTicket.id)).where(
            SupportTicket.status.in_(["open", "in_progress", "waiting_user", "waiting_for_user"])
        ))).scalar() or 0

        # Practice & Coding & Contests
        db_tech_questions = (await db.execute(select(func.count(PracticeQuestion.id)))).scalar() or 0
        db_coding_problems = (await db.execute(select(func.count(CodingProblem.id)))).scalar() or 0
        db_coding_submissions = (await db.execute(select(func.count(CodingSubmission.id)))).scalar() or 0
        db_contests = (await db.execute(select(func.count(Contest.id)))).scalar() or 0
        db_rag_vectors = (await db.execute(select(func.count(InterviewQuestionVector.id)))).scalar() or 0

        # Daily chart aggregations
        int_stmt = (
            select(cast(Interview.created_at, Date).label("d"), func.count(Interview.id).label("cnt"))
            .where(Interview.created_at >= since_30d)
            .group_by(cast(Interview.created_at, Date))
            .order_by(cast(Interview.created_at, Date))
        )
        db_interview_daily_map = {row.d.isoformat(): row.cnt for row in (await db.execute(int_stmt)).all()}

        u_stmt = (
            select(cast(User.created_at, Date).label("d"), func.count(User.id).label("cnt"))
            .where(User.created_at >= since_30d)
            .group_by(cast(User.created_at, Date))
            .order_by(cast(User.created_at, Date))
        )
        db_user_daily_map = {row.d.isoformat(): row.cnt for row in (await db.execute(u_stmt)).all()}

        rev_stmt = (
            select(cast(PaymentTransaction.created_at, Date).label("d"), func.sum(PaymentTransaction.amount).label("amt"))
            .where(and_(PaymentTransaction.created_at >= since_30d, PaymentTransaction.status == "paid"))
            .group_by(cast(PaymentTransaction.created_at, Date))
            .order_by(cast(PaymentTransaction.created_at, Date))
        )
        db_rev_daily_map = {row.d.isoformat(): round(float(row.amt) / 100.0, 2) for row in (await db.execute(rev_stmt)).all()}

    # 4. Cross-check KPI by KPI
    print("\n[Step 4] Cross-checking every KPI (Expected DB vs Actual API)...")
    checks = [
        ("Total users", db_total_users, api_data.get("total_users")),
        ("Active users", db_active_users, api_data.get("active_users")),
        ("New users (30d)", db_new_users_30d, api_data.get("new_users_30d")),
        ("Total interviews", db_total_interviews, api_data.get("total_interviews")),
        ("Completed interviews", db_completed_interviews, api_data.get("completed_interviews")),
        ("Average interview score", db_avg_interview_score, api_data.get("avg_interview_score")),
        ("Average ATS score", db_avg_ats_score, api_data.get("avg_ats_score")),
        ("Active subscriptions", db_active_subs, api_data.get("active_subscriptions")),
        ("Total subscription plans", db_total_plans, api_data.get("total_subscription_plans")),
        ("Expired subscriptions", db_expired_subs, api_data.get("expired_subscriptions")),
        ("Total revenue (INR)", db_revenue_inr, api_data.get("total_revenue_inr")),
        ("Total payment transactions", db_total_payments, api_data.get("total_payment_transactions")),
        ("Successful payments", db_successful_payments, api_data.get("successful_payments")),
        ("Failed payments", db_failed_payments, api_data.get("failed_payments")),
        ("Pending support tickets", db_pending_tickets, api_data.get("pending_support_tickets")),
        ("Open support tickets", db_open_tickets, api_data.get("open_support_tickets")),
        ("In-progress support tickets", db_in_prog_tickets, api_data.get("in_progress_support_tickets")),
        ("Total support tickets", db_total_tickets, api_data.get("total_support_tickets")),
        ("Technical questions", db_tech_questions, api_data.get("technical_questions")),
        ("Coding problems", db_coding_problems, api_data.get("coding_problems")),
        ("Coding submissions", db_coding_submissions, api_data.get("total_coding_submissions")),
        ("Contests", db_contests, api_data.get("contests")),
        ("RAG indexed vectors", db_rag_vectors, api_data.get("rag_question_count")),
    ]

    all_passed = True
    for label, expected, actual in checks:
        passed = (expected == actual) or (expected is None and actual is None)
        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status_str} {label:<30} | Expected DB: {str(expected):<10} | Actual API: {str(actual):<10}")

    assert all_passed, "One or more KPI values failed database cross-check!"

    # 5. Cross-check Time-Series Charts
    print("\n[Step 5] Cross-checking time-series date aggregation charts...")
    # Chart 1: Interview activity
    chart_int = api_data.get("interview_activity_chart", [])
    assert len(chart_int) > 0, "Interview chart is empty"
    for pt in chart_int:
        d = pt["date"]
        exp = db_interview_daily_map.get(d, 0)
        assert pt["value"] == exp, f"Interview chart mismatch on {d}: expected {exp}, got {pt['value']}"
    print(f"[PASS] Chart 1 (Interview Activity): {len(chart_int)} points match PostgreSQL date aggregation.")

    # Chart 2: User registrations
    chart_u = api_data.get("user_growth_chart", [])
    assert len(chart_u) > 0, "User growth chart is empty"
    for pt in chart_u:
        d = pt["date"]
        exp = db_user_daily_map.get(d, 0)
        assert pt["value"] == exp, f"User growth chart mismatch on {d}: expected {exp}, got {pt['value']}"
    print(f"[PASS] Chart 2 (User Growth): {len(chart_u)} points match PostgreSQL date aggregation.")

    # Chart 3: Revenue
    chart_rev = api_data.get("revenue_chart", [])
    assert len(chart_rev) > 0, "Revenue chart is empty"
    for pt in chart_rev:
        d = pt["date"]
        exp = db_rev_daily_map.get(d, 0.0)
        assert abs(pt["value"] - exp) < 0.01, f"Revenue chart mismatch on {d}: expected {exp}, got {pt['value']}"
    print(f"[PASS] Chart 3 (Revenue INR): {len(chart_rev)} points match PostgreSQL date aggregation.")

    # 6. Verify Date Range Filtering
    print("\n[Step 6] Testing date range filters (today, 7d, 30d, 90d, year, all)...")
    for r in ["today", "7d", "30d", "90d", "this_year", "year", "all"]:
        c, r_data = http_request("GET", f"/admin/dashboard?time_range={r}", token=token)
        assert c == 200, f"Date filter {r} returned {c}"
        assert "user_growth_chart" in r_data and len(r_data["user_growth_chart"]) > 0
        print(f"[PASS] Range filter '{r}': Returned {len(r_data['user_growth_chart'])} timeline points.")

    # 7. Check Nested KPI & Trends Structure (Frontend Compatibility)
    print("\n[Step 7] Checking frontend contract compatibility (kpis, trends, recent_activities)...")
    assert "kpis" in api_data and isinstance(api_data["kpis"], dict), "Missing kpis dict"
    assert "trends" in api_data and isinstance(api_data["trends"], dict), "Missing trends dict"
    assert "recent_activities" in api_data and isinstance(api_data["recent_activities"], list), "Missing recent_activities list"
    assert "interviews_daily" in api_data["trends"], "Missing interviews_daily in trends"
    assert "user_registrations_daily" in api_data["trends"], "Missing user_registrations_daily in trends"
    assert "revenue_daily" in api_data["trends"], "Missing revenue_daily in trends"
    assert api_data["kpis"]["total_users"] == db_total_users
    assert api_data["kpis"]["total_revenue_inr"] == db_revenue_inr
    print(f"[PASS] Frontend contract verified with {len(api_data['recent_activities'])} audit events.")

    print("\n" + "=" * 70)
    print("ALL ADMIN DASHBOARD KPI & ANALYTICS VERIFICATIONS PASSED (100% ACCURATE)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
