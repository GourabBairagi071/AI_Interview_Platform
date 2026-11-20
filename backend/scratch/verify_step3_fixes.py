import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath("."))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from sqlalchemy import select

async def run_step3_verification():
    print("=== STEP 3: FUNCTIONAL VERIFICATION OF ADMIN FIXES ===")
    
    async with AsyncSessionLocal() as db:
        # Get super admin user and candidate user
        admin_res = await db.execute(select(User).where(User.role == "SUPER_ADMIN").limit(1))
        admin_user = admin_res.scalar_one_or_none()
        if not admin_user:
            admin_res = await db.execute(select(User).where(User.role == "ADMIN").limit(1))
            admin_user = admin_res.scalar_one_or_none()
        
        cand_res = await db.execute(select(User).where(User.role == "CANDIDATE").limit(1))
        cand_user = cand_res.scalar_one_or_none()

    if not admin_user:
        print("ERROR: No admin user found for verification")
        return False
    print(f"Verified Admin User: {admin_user.email} ({admin_user.role})")
    if cand_user:
        print(f"Verified Candidate User: {cand_user.email} ({cand_user.role})")

    # Generate auth tokens
    from app.core.security import create_access_token
    admin_token = create_access_token(str(admin_user.id))
    cand_token = create_access_token(str(cand_user.id)) if cand_user else None

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    cand_headers = {"Authorization": f"Bearer {cand_token}"} if cand_token else {}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Admin Coding Problems page loads
        print("\n1. Testing GET /api/v1/admin/coding/problems...")
        resp = await client.get("/api/v1/admin/coding/problems?page=1&page_size=5", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "problems" in data and len(data["problems"]) > 0, "No problems returned"
        assert "acceptance_rate" in data["problems"][0], "acceptance_rate key missing"
        print(f"   SUCCESS: Loaded {len(data['problems'])} problems. Total in DB: {data.get('total')}")

        # 2. Candidate 360 opens
        target_id = str(cand_user.id) if cand_user else str(admin_user.id)
        print(f"\n2. Testing GET /api/v1/admin/candidates/{target_id}/360...")
        resp = await client.get(f"/api/v1/admin/candidates/{target_id}/360", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        c360 = resp.json()
        assert "interviews" in c360, "Interviews missing in candidate 360"
        assert "coding_submissions" in c360, "Submissions missing in candidate 360"
        print(f"   SUCCESS: Candidate 360 loaded successfully. Interviews: {len(c360['interviews'])}, Submissions: {len(c360['coding_submissions'])}")

        # 3. Question creation works
        print("\n3. Testing POST /api/v1/admin/questions...")
        q_payload = {
            "technology": "Python",
            "topic": "Algorithms",
            "subtopic": "Dynamic Programming",
            "question": f"Test question for verification {uuid.uuid4().hex[:6]}",
            "difficulty": "Medium",
            "question_type": "Technical",
            "explanation": "Memoization optimizes recursion."
        }
        resp = await client.post("/api/v1/admin/questions", json=q_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_q = resp.json()
        print(f"   SUCCESS: Created question ID: {created_q.get('id')}")

        # 4. Company creation works
        print("\n4. Testing POST /api/v1/admin/companies...")
        comp_payload = {
            "name": f"VerifTech {uuid.uuid4().hex[:4]}",
            "industry": "Technology",
            "difficulty": "Hard",
            "roles": ["Software Engineer", "Site Reliability Engineer"],
            "interview_types": ["Technical", "System Design"],
            "description": "High frequency trading and distributed systems."
        }
        resp = await client.post("/api/v1/admin/companies", json=comp_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_comp = resp.json()
        print(f"   SUCCESS: Created company ID: {created_comp.get('id')}, Name: {created_comp.get('name')}")

        # 5. Resource creation works
        print("\n5. Testing POST /api/v1/admin/resources...")
        res_payload = {
            "title": f"Distributed Caching Deep Dive {uuid.uuid4().hex[:4]}",
            "topic": "System Design",
            "canonical_skill": "System Design",
            "difficulty": "Intermediate",
            "resource_type": "Documentation",
            "description": "Comprehensive guide to Redis and Memcached architectures."
        }
        resp = await client.post("/api/v1/admin/resources", json=res_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_res = resp.json()
        print(f"   SUCCESS: Created resource ID: {created_res.get('id')}")

        # 6. Subscription plan creation works
        print("\n6. Testing POST /api/v1/admin/subscriptions/plans...")
        sub_payload = {
            "plan_code": f"TEST_TIER_{uuid.uuid4().hex[:4].upper()}",
            "name": "Elite Mentorship Plan",
            "description": "Unlimited interview practice and dedicated mock tests",
            "price_inr": 1999.0,
            "duration_days": 30,
            "interview_limit": 20,
            "resume_analyses_limit": 10,
            "coding_practice_unlimited": True,
            "is_active": True
        }
        resp = await client.post("/api/v1/admin/subscriptions/plans", json=sub_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_plan = resp.json()
        print(f"   SUCCESS: Created subscription plan: {created_plan.get('plan_code')}")

        # 7. Coupon creation works
        print("\n7. Testing POST /api/v1/admin/coupons...")
        now = datetime.now(timezone.utc)
        coupon_payload = {
            "code": f"VERIF{uuid.uuid4().hex[:4].upper()}",
            "discount_type": "PERCENTAGE",
            "discount_value": 25.0,
            "max_discount_inr": 500.0,
            "min_order_inr": 0.0,
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=365)).isoformat(),
            "usage_limit": 100
        }
        resp = await client.post("/api/v1/admin/coupons", json=coupon_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_coupon = resp.json()
        print(f"   SUCCESS: Created coupon: {created_coupon.get('code')}")

        # 8. Achievement creation works
        print("\n8. Testing POST /api/v1/admin/achievements...")
        ach_payload = {
            "id": f"milestone_{uuid.uuid4().hex[:6]}",
            "name": "Master Architect",
            "description": "Completed 5 complex system design interviews with >85% score",
            "category": "INTERVIEW",
            "icon": "trophy",
            "rarity": "Legendary",
            "xp_reward": 250,
            "target_value": 5,
            "is_active": True
        }
        resp = await client.post("/api/v1/admin/achievements", json=ach_payload, headers=admin_headers)
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        created_ach = resp.json()
        print(f"   SUCCESS: Created achievement: {created_ach.get('id')}")

        # 9. Test unauthorized access and RBAC
        print("\n9. Testing Security & RBAC Enforcement...")
        # Unauthenticated request
        unauth_resp = await client.get("/api/v1/admin/coding/problems")
        assert unauth_resp.status_code in [401, 403], f"Expected 401/403 for unauth, got {unauth_resp.status_code}"
        print(f"   SUCCESS: Unauthenticated access blocked with HTTP {unauth_resp.status_code}")

        # Candidate user attempting admin endpoint
        if cand_headers:
            cand_resp = await client.get("/api/v1/admin/coding/problems", headers=cand_headers)
            assert cand_resp.status_code in [401, 403], f"Expected 403 for candidate, got {cand_resp.status_code}"
            print(f"   SUCCESS: Candidate access to admin endpoint blocked with HTTP {cand_resp.status_code}")

        # 10. Test persistence on reload
        print("\n10. Testing Persistence After Refresh...")
        get_res = await client.get(f"/api/v1/admin/questions?search={q_payload['question']}", headers=admin_headers)
        assert get_res.status_code == 200
        found_questions = get_res.json().get("questions", [])
        assert any(q.get("question") == q_payload["question"] for q in found_questions), "Created question not retrieved"
        print(f"   SUCCESS: Question persists and is queryable after refresh!")

    print("\n>>> ALL STEP 3 VERIFICATIONS PASSED WITH ZERO ERRORS! <<<")
    return True

if __name__ == "__main__":
    asyncio.run(run_step3_verification())
