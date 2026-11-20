import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_step14_regression():
    print("=== STARTING STEP 14: FULL SYSTEM REGRESSION VERIFICATION ===")

    # 1. Auth Setup
    admin_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    rand_suffix = uuid.uuid4().hex[:6]
    cand_email = f"cand_reg_{rand_suffix}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": cand_email,
        "full_name": f"Candidate Regression {rand_suffix}",
        "password": "Password@123",
        "role": "candidate"
    })
    cand_login = requests.post(f"{BASE_URL}/auth/login", json={"email": cand_email, "password": "Password@123"})
    cand_token = cand_login.json()["access_token"]
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # Regression Test Matrix Across Core Platform Modules
    regression_checks = {
        "1_authentication_login": admin_login.status_code == 200 and cand_login.status_code == 200,
        "2_candidate_profile": requests.get(f"{BASE_URL}/profile", headers=cand_headers).status_code == 200,
        "3_candidate_dashboard_config": requests.get(f"{BASE_URL}/dashboard/config", headers=cand_headers).status_code == 200,
        "4_candidate_dashboard_featured": requests.get(f"{BASE_URL}/dashboard/featured", headers=cand_headers).status_code == 200,
        "5_coding_problems_candidate": requests.get(f"{BASE_URL}/coding/problems?page=1&page_size=5", headers=cand_headers).status_code == 200,
        "6_contests_candidate": requests.get(f"{BASE_URL}/contests", headers=cand_headers).status_code == 200,
        "7_question_practice_candidate": requests.get(f"{BASE_URL}/practice/questions", headers=cand_headers).status_code == 200,
        "8_learning_resources": requests.get(f"{BASE_URL}/admin/resources", headers=admin_headers).status_code == 200,
        "9_support_tickets": requests.get(f"{BASE_URL}/support/tickets", headers=cand_headers).status_code == 200,
        "10_notifications": requests.get(f"{BASE_URL}/notifications", headers=cand_headers).status_code == 200,
        "11_admin_users": requests.get(f"{BASE_URL}/admin/users?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "12_admin_interviews": requests.get(f"{BASE_URL}/admin/interviews?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "13_admin_questions": requests.get(f"{BASE_URL}/admin/questions?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "14_admin_companies": requests.get(f"{BASE_URL}/admin/companies?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "15_admin_resources": requests.get(f"{BASE_URL}/admin/resources?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "16_admin_subscription_plans": requests.get(f"{BASE_URL}/admin/subscriptions/plans", headers=admin_headers).status_code == 200,
        "17_admin_payments": requests.get(f"{BASE_URL}/admin/payments?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "18_admin_coupons": requests.get(f"{BASE_URL}/admin/coupons?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "19_admin_invoices": requests.get(f"{BASE_URL}/admin/invoices?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "20_admin_achievements": requests.get(f"{BASE_URL}/admin/achievements?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "21_admin_audit_logs": requests.get(f"{BASE_URL}/admin/audit-logs?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "22_admin_rbac_roles": requests.get(f"{BASE_URL}/admin/rbac/roles", headers=admin_headers).status_code == 200,
        "23_admin_assignments": requests.get(f"{BASE_URL}/admin/assignments?page=1&page_size=5", headers=admin_headers).status_code == 200,
        "24_candidate_assignments": requests.get(f"{BASE_URL}/candidate/assignments", headers=cand_headers).status_code == 200,
    }

    all_passed = all(v for v in regression_checks.values())

    output = {
        "regression_results": regression_checks,
        "total_checks": len(regression_checks),
        "passed_checks": sum(1 for v in regression_checks.values() if v),
        "failed_checks": sum(1 for v in regression_checks.values() if not v),
        "status": "VERIFIED" if all_passed else "FAILED"
    }

    with open("scratch/step14_regression_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n============================================================")
    print("STEP 14 FULL SYSTEM REGRESSION SUMMARY")
    print("============================================================")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run_step14_regression()
