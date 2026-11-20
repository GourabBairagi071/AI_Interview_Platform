import asyncio
import sys
import uuid
import datetime
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def main():
    print("RUNNING LIVE VERIFICATION FOR DEEP FUNCTIONAL AUDIT")
    # 1. Admin Auth
    admin_login = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@interviewplatform.ai", "password": "AdminPass123!"})
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Candidate Auth
    cand_login = requests.post(f"{BASE_URL}/auth/login", json={"email": "candidate_test@example.com", "password": "Password123!"})
    if cand_login.status_code != 200:
        cand_reg = requests.post(f"{BASE_URL}/auth/register", json={"email": "candidate_test@example.com", "full_name": "Test Candidate", "password": "Password123!", "role": "candidate"})
        cand_login = requests.post(f"{BASE_URL}/auth/login", json={"email": "candidate_test@example.com", "password": "Password123!"})
    cand_token = cand_login.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    cand_id = cand_login.json()["user"]["id"]

    results = {}
    
    # Area 1: Admin Auth & Me
    me = requests.get(f"{BASE_URL}/admin/me", headers=admin_headers)
    results["01_admin_auth"] = (me.status_code == 200 and me.json().get("is_admin") is True)
    
    # Area 2: Admin Dashboard
    dash = requests.get(f"{BASE_URL}/admin/dashboard?time_range=30d", headers=admin_headers)
    results["02_admin_dashboard"] = (dash.status_code == 200 and "kpis" in dash.json())

    # Area 3: KPI / Analytics
    results["03_kpi_analytics"] = (dash.status_code == 200 and isinstance(dash.json()["kpis"].get("total_candidates"), int))

    # Area 4: Candidate Management
    users = requests.get(f"{BASE_URL}/admin/users?role=CANDIDATE", headers=admin_headers)
    c360 = requests.get(f"{BASE_URL}/admin/candidates/{cand_id}/360", headers=admin_headers)
    results["04_candidate_management"] = (users.status_code == 200 and c360.status_code == 200)

    # Area 5: Interview Management
    interviews = requests.get(f"{BASE_URL}/admin/interviews", headers=admin_headers)
    results["05_interview_management"] = (interviews.status_code == 200 and "interviews" in interviews.json())

    # Area 6: Interview Templates
    # GET /admin/interview-configs
    configs = requests.get(f"{BASE_URL}/admin/interview-configs", headers=admin_headers)
    results["06_interview_templates"] = (configs.status_code == 200)

    # Area 7: Practice Questions
    # Check POST /admin/questions with correct technology field
    q_post = requests.post(f"{BASE_URL}/admin/questions", json={
        "technology": "Python",
        "topic": "Algorithms",
        "question": "What is binary search time complexity?",
        "difficulty": "Easy",
        "question_type": "Technical",
        "explanation": "O(log n)"
    }, headers=admin_headers)
    results["07_practice_questions"] = (q_post.status_code == 200)

    # Area 8: Coding Problems
    cp = requests.get(f"{BASE_URL}/admin/coding/problems?page_size=1", headers=admin_headers)
    results["08_coding_problems"] = (cp.status_code == 200 and cp.json().get("total", 0) >= 1000)

    # Area 9: Contest Management
    contests = requests.get(f"{BASE_URL}/admin/contests", headers=admin_headers)
    results["09_contest_management"] = (contests.status_code == 200)

    # Area 10: Company Management
    companies = requests.get(f"{BASE_URL}/admin/companies", headers=admin_headers)
    results["10_company_management"] = (companies.status_code == 200)

    # Area 11: Learning Roadmaps
    roadmaps = requests.get(f"{BASE_URL}/admin/roadmaps", headers=admin_headers)
    results["11_learning_roadmaps"] = (roadmaps.status_code == 200)

    # Area 12: Learning Resources
    resources = requests.get(f"{BASE_URL}/admin/resources", headers=admin_headers)
    results["12_learning_resources"] = (resources.status_code == 200)

    # Area 13: Practice Sets / Mock Tests
    psets = requests.get(f"{BASE_URL}/admin/practice-sets", headers=admin_headers)
    results["13_practice_sets"] = (psets.status_code == 200)

    # Area 14: AI Agent Management
    agents = requests.get(f"{BASE_URL}/admin/ai-agents", headers=admin_headers)
    results["14_ai_agents"] = (agents.status_code == 200)

    # Area 15: RAG / Question Bank
    rag = requests.get(f"{BASE_URL}/admin/rag/status", headers=admin_headers)
    results["15_rag_management"] = (rag.status_code == 200 and rag.json().get("indexed_questions_count", 0) >= 5000)

    # Area 16: Resume / ATS Management
    resumes = requests.get(f"{BASE_URL}/admin/resume-ats", headers=admin_headers)
    results["16_resume_ats"] = (resumes.status_code == 200)

    # Area 17: Subscription Management
    plans = requests.get(f"{BASE_URL}/admin/subscriptions/plans", headers=admin_headers)
    results["17_subscriptions"] = (plans.status_code == 200 and len(plans.json()) >= 3)

    # Area 18: Payment Management
    payments = requests.get(f"{BASE_URL}/admin/payments", headers=admin_headers)
    results["18_payments"] = (payments.status_code == 200)

    # Area 19: Coupons
    coupons = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
    results["19_coupons"] = (coupons.status_code == 200)

    # Area 20: Invoices
    invoices = requests.get(f"{BASE_URL}/admin/invoices", headers=admin_headers)
    results["20_invoices"] = (invoices.status_code == 200)

    # Area 21: Support
    tickets = requests.get(f"{BASE_URL}/admin/support/tickets", headers=admin_headers)
    results["21_support"] = (tickets.status_code == 200)

    # Area 22: Feedback
    feedback = requests.get(f"{BASE_URL}/admin/feedback", headers=admin_headers)
    results["22_feedback"] = (feedback.status_code == 200)

    # Area 23: Notifications
    bnotif = requests.post(f"{BASE_URL}/admin/notifications/broadcast", json={
        "title": "Audit Ping",
        "message": "Audit verification broadcast",
        "type": "system",
        "target_role": "CANDIDATE"
    }, headers=admin_headers)
    results["23_notifications"] = (bnotif.status_code == 200)

    # Area 24: Achievements
    achs = requests.get(f"{BASE_URL}/admin/achievements", headers=admin_headers)
    results["24_achievements"] = (achs.status_code == 200)

    # Area 25: Platform Settings
    settings = requests.get(f"{BASE_URL}/admin/settings", headers=admin_headers)
    results["25_platform_settings"] = (settings.status_code == 200)

    # Area 26: Candidate Dashboard Controls
    dash_cfg = requests.get(f"{BASE_URL}/admin/dashboard-config", headers=admin_headers)
    results["26_dashboard_controls"] = (dash_cfg.status_code == 200)

    # Area 27: Featured Content
    feat = requests.get(f"{BASE_URL}/admin/featured-content", headers=admin_headers)
    results["27_featured_content"] = (feat.status_code == 200)

    # Area 28: RBAC
    rbac = requests.get(f"{BASE_URL}/admin/rbac/roles", headers=admin_headers)
    results["28_rbac"] = (rbac.status_code == 200)

    # Area 29: Audit Logs
    audit = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
    results["29_audit_logs"] = (audit.status_code == 200 and len(audit.json().get("logs", [])) > 0)

    # Area 30: Security Controls (Candidate Blocked from Admin)
    cand_blocked = requests.get(f"{BASE_URL}/admin/dashboard", headers=cand_headers)
    results["30_security_controls"] = (cand_blocked.status_code == 403)

    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        print(f"[{status}] {k}")

if __name__ == "__main__":
    main()
