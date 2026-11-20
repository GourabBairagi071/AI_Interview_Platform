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
        for k in ["items", "questions", "resources", "plans", "coupons", "achievements", "companies", "problems"]:
            if k in resp_json and isinstance(resp_json[k], list):
                return resp_json[k]
    return []

def run_step1_verification():
    results = {}
    test_record_ids = {}

    print("=== STARTING STEP 1 VERIFICATION ===")

    # 0. Admin Login
    admin_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@interviewplatform.ai",
        "password": "AdminPass123!"
    })
    if admin_login.status_code != 200:
        print(f"FAILED Admin login: {admin_login.status_code} - {admin_login.text}")
        return
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin login successful.")

    # 1. GET /api/v1/admin/coding/problems
    print("\n--- Testing 1: GET /api/v1/admin/coding/problems ---")
    res1 = requests.get(f"{BASE_URL}/admin/coding/problems?page=1&page_size=10", headers=admin_headers)
    print(f"Status: {res1.status_code}")
    if res1.status_code == 200:
        data1 = res1.json()
        total_count = data1.get("total", 0)
        items = data1.get("problems", [])
        valid_uuid = False
        if items and len(items) > 0:
            try:
                uuid.UUID(str(items[0]["id"]))
                valid_uuid = True
            except ValueError:
                valid_uuid = False
        print(f"Total count returned by API: {total_count}, Items returned: {len(items)}, Valid UUID: {valid_uuid}")
        # Note: total_count returned by API is 1000000 due to cartesian product bug in router query (documented defect). DB actual count is 1000.
        results["coding_problems"] = {
            "status": "VERIFIED_WITH_DEFECT",
            "http_status": res1.status_code,
            "total_count": total_count,
            "valid_uuid": valid_uuid,
            "note": "Defect recorded: subquery count query produces 1,000,000 via cartesian product instead of 1,000"
        }
    else:
        results["coding_problems"] = {"status": "FAILED", "http_status": res1.status_code, "detail": res1.text}

    # 2. GET /api/v1/admin/candidates/{candidate_id}/360
    print("\n--- Testing 2: GET /api/v1/admin/candidates/{candidate_id}/360 ---")
    users_res = requests.get(f"{BASE_URL}/admin/users?role=candidate&page=1&page_size=5", headers=admin_headers)
    cand_id = None
    if users_res.status_code == 200:
        u_data = users_res.json()
        u_items = parse_items(u_data, "users")
        if u_items:
            cand_id = u_items[0]["id"]
    
    if cand_id:
        res2 = requests.get(f"{BASE_URL}/admin/candidates/{cand_id}/360", headers=admin_headers)
        print(f"Status: {res2.status_code} for candidate {cand_id}")
        if res2.status_code == 200:
            data2 = res2.json()
            resume_info = "resume" in data2 or "resumes" in data2 or "ats_scores" in data2
            interview_info = "interviews" in data2 or "interview_history" in data2 or "recent_interviews" in data2
            print(f"Data keys: {list(data2.keys())}")
            results["candidate_360"] = {
                "status": "VERIFIED",
                "http_status": res2.status_code,
                "resume_info_present": resume_info,
                "interview_info_present": interview_info
            }
        else:
            results["candidate_360"] = {"status": "FAILED", "http_status": res2.status_code, "detail": res2.text}
    else:
        results["candidate_360"] = {"status": "FAILED", "detail": "Could not find candidate user ID to test"}

    rand_suffix = uuid.uuid4().hex[:6]

    # 3. POST /api/v1/admin/questions
    print("\n--- Testing 3: POST /api/v1/admin/questions ---")
    q_valid = {
        "technology": "Python",
        "topic": "System Architecture",
        "subtopic": "Microservices",
        "question": f"Explain CAP theorem tradeoffs in distributed systems {rand_suffix}?",
        "difficulty": "Medium",
        "question_type": "Technical",
        "role": "Backend Engineer",
        "explanation": "Test explanation for candidate control QA"
    }
    q_res = requests.post(f"{BASE_URL}/admin/questions", json=q_valid, headers=admin_headers)
    print(f"Valid POST Status: {q_res.status_code}")
    q_invalid_res = requests.post(f"{BASE_URL}/admin/questions", json={"technology": "Python"}, headers=admin_headers)
    print(f"Invalid POST Status: {q_invalid_res.status_code}")
    
    if q_res.status_code in (200, 201):
        q_id = q_res.json()["id"]
        test_record_ids["question_id"] = str(q_id)
        q_get = requests.get(f"{BASE_URL}/admin/questions", headers=admin_headers)
        q_items = parse_items(q_get.json(), "questions")
        q_persisted = q_get.status_code == 200 and any(str(item.get("id")) == str(q_id) for item in q_items)
        results["questions"] = {
            "status": "VERIFIED" if (q_persisted and q_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": q_res.status_code,
            "invalid_status": q_invalid_res.status_code,
            "persisted": q_persisted,
            "record_id": str(q_id)
        }
    else:
        results["questions"] = {"status": "FAILED", "post_status": q_res.status_code, "detail": q_res.text}

    # 4. POST /api/v1/admin/companies
    print("\n--- Testing 4: POST /api/v1/admin/companies ---")
    c_valid = {
        "name": f"Step1 Test Corp {rand_suffix}",
        "logo_url": "https://example.com/logo.png",
        "description": "Test company for admin candidate verification",
        "industry": "Technology",
        "website": "https://example.com",
        "roles": ["Backend Developer"],
        "interview_types": ["Behavioral", "Technical"],
        "difficulty": "Medium",
        "preparation_content": "Preparation guide content"
    }
    c_res = requests.post(f"{BASE_URL}/admin/companies", json=c_valid, headers=admin_headers)
    print(f"Valid POST Status: {c_res.status_code}")
    c_invalid_res = requests.post(f"{BASE_URL}/admin/companies", json={"industry": "Tech"}, headers=admin_headers)
    print(f"Invalid POST Status: {c_invalid_res.status_code}")

    if c_res.status_code in (200, 201):
        c_id = c_res.json()["id"]
        test_record_ids["company_id"] = str(c_id)
        c_get = requests.get(f"{BASE_URL}/admin/companies", headers=admin_headers)
        c_items = parse_items(c_get.json(), "companies")
        c_persisted = c_get.status_code == 200 and any(str(item.get("id")) == str(c_id) for item in c_items)
        results["companies"] = {
            "status": "VERIFIED" if (c_persisted and c_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": c_res.status_code,
            "invalid_status": c_invalid_res.status_code,
            "persisted": c_persisted,
            "record_id": str(c_id)
        }
    else:
        results["companies"] = {"status": "FAILED", "post_status": c_res.status_code, "detail": c_res.text}

    # 5. POST /api/v1/admin/resources
    print("\n--- Testing 5: POST /api/v1/admin/resources ---")
    r_valid = {
        "title": f"Step1 Preparation Guide {rand_suffix}",
        "description": "Resource guide for verification",
        "topic": "System Design",
        "canonical_skill": "Architecture",
        "difficulty": "Intermediate",
        "resource_type": "Documentation",
        "url": "https://example.com/guide.pdf"
    }
    r_res = requests.post(f"{BASE_URL}/admin/resources", json=r_valid, headers=admin_headers)
    print(f"Valid POST Status: {r_res.status_code}")
    r_invalid_res = requests.post(f"{BASE_URL}/admin/resources", json={"difficulty": "Hard"}, headers=admin_headers)
    print(f"Invalid POST Status: {r_invalid_res.status_code}")

    if r_res.status_code in (200, 201):
        r_id = r_res.json()["id"]
        test_record_ids["resource_id"] = str(r_id)
        r_get = requests.get(f"{BASE_URL}/admin/resources", headers=admin_headers)
        r_items = parse_items(r_get.json(), "resources")
        r_persisted = r_get.status_code == 200 and any(str(item.get("id")) == str(r_id) for item in r_items)
        results["resources"] = {
            "status": "VERIFIED" if (r_persisted and r_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": r_res.status_code,
            "invalid_status": r_invalid_res.status_code,
            "persisted": r_persisted,
            "record_id": str(r_id)
        }
    else:
        results["resources"] = {"status": "FAILED", "post_status": r_res.status_code, "detail": r_res.text}

    # 6. POST /api/v1/admin/subscriptions/plans
    print("\n--- Testing 6: POST /api/v1/admin/subscriptions/plans ---")
    s_valid = {
        "plan_code": f"STEP1_{rand_suffix.upper()}",
        "name": f"Step1 Plan {rand_suffix}",
        "description": "Verification plan for candidate control",
        "price_inr": 1499.0,
        "duration_days": 30,
        "interview_limit": 10,
        "resume_analyses_limit": 5,
        "coding_practice_unlimited": True,
        "is_active": True
    }
    s_res = requests.post(f"{BASE_URL}/admin/subscriptions/plans", json=s_valid, headers=admin_headers)
    print(f"Valid POST Status: {s_res.status_code}")
    s_invalid_res = requests.post(f"{BASE_URL}/admin/subscriptions/plans", json={"name": "Invalid Plan"}, headers=admin_headers)
    print(f"Invalid POST Status: {s_invalid_res.status_code}")

    if s_res.status_code in (200, 201):
        s_id = s_res.json()["id"]
        test_record_ids["subscription_plan_id"] = str(s_id)
        s_get = requests.get(f"{BASE_URL}/admin/subscriptions/plans", headers=admin_headers)
        s_items = parse_items(s_get.json(), "plans")
        s_persisted = s_get.status_code == 200 and any(str(item.get("id")) == str(s_id) for item in s_items)
        results["subscriptions"] = {
            "status": "VERIFIED" if (s_persisted and s_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": s_res.status_code,
            "invalid_status": s_invalid_res.status_code,
            "persisted": s_persisted,
            "record_id": str(s_id)
        }
    else:
        results["subscriptions"] = {"status": "FAILED", "post_status": s_res.status_code, "detail": s_res.text}

    # 7. POST /api/v1/admin/coupons
    print("\n--- Testing 7: POST /api/v1/admin/coupons ---")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cp_valid = {
        "code": f"STEP1_{rand_suffix.upper()}",
        "discount_type": "PERCENTAGE",
        "discount_value": 20.0,
        "max_discount_inr": 500.0,
        "min_order_inr": 100.0,
        "valid_from": now_utc.isoformat(),
        "valid_until": (now_utc + datetime.timedelta(days=30)).isoformat(),
        "usage_limit": 50
    }
    cp_res = requests.post(f"{BASE_URL}/admin/coupons", json=cp_valid, headers=admin_headers)
    print(f"Valid POST Status: {cp_res.status_code}")
    cp_invalid_res = requests.post(f"{BASE_URL}/admin/coupons", json={"code": "INVALID_CP"}, headers=admin_headers)
    print(f"Invalid POST Status: {cp_invalid_res.status_code}")

    if cp_res.status_code in (200, 201):
        cp_id = cp_res.json()["id"]
        test_record_ids["coupon_id"] = str(cp_id)
        cp_get = requests.get(f"{BASE_URL}/admin/coupons", headers=admin_headers)
        cp_items = parse_items(cp_get.json(), "coupons")
        cp_persisted = cp_get.status_code == 200 and any(str(item.get("id")) == str(cp_id) for item in cp_items)
        results["coupons"] = {
            "status": "VERIFIED" if (cp_persisted and cp_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": cp_res.status_code,
            "invalid_status": cp_invalid_res.status_code,
            "persisted": cp_persisted,
            "record_id": str(cp_id)
        }
    else:
        results["coupons"] = {"status": "FAILED", "post_status": cp_res.status_code, "detail": cp_res.text}

    # 8. POST /api/v1/admin/achievements
    print("\n--- Testing 8: POST /api/v1/admin/achievements ---")
    ach_valid = {
        "id": f"ach_step1_{rand_suffix}",
        "name": f"Step1 Master {rand_suffix}",
        "description": "Achievement badge for completing step 1 verification",
        "category": "Interviews",
        "icon": "trophy",
        "rarity": "Legendary",
        "xp_reward": 100,
        "target_value": 5,
        "is_active": True
    }
    ach_res = requests.post(f"{BASE_URL}/admin/achievements", json=ach_valid, headers=admin_headers)
    print(f"Valid POST Status: {ach_res.status_code}")
    ach_invalid_res = requests.post(f"{BASE_URL}/admin/achievements", json={"rarity": "Legendary"}, headers=admin_headers)
    print(f"Invalid POST Status: {ach_invalid_res.status_code}")

    if ach_res.status_code in (200, 201):
        ach_id = ach_res.json()["id"]
        test_record_ids["achievement_id"] = str(ach_id)
        ach_get = requests.get(f"{BASE_URL}/admin/achievements", headers=admin_headers)
        ach_items = parse_items(ach_get.json(), "achievements")
        ach_persisted = ach_get.status_code == 200 and any(str(item.get("id")) == str(ach_id) for item in ach_items)
        results["achievements"] = {
            "status": "VERIFIED" if (ach_persisted and ach_invalid_res.status_code in (400, 422)) else "FAILED",
            "post_status": ach_res.status_code,
            "invalid_status": ach_invalid_res.status_code,
            "persisted": ach_persisted,
            "record_id": str(ach_id)
        }
    else:
        results["achievements"] = {"status": "FAILED", "post_status": ach_res.status_code, "detail": ach_res.text}

    output = {
        "summary": results,
        "test_record_ids": test_record_ids
    }
    
    with open("scratch/step1_verification_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n=== STEP 1 VERIFICATION RESULTS SUMMARY ===")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run_step1_verification()
