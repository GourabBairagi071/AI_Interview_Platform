import asyncio
import sys
import uuid
import httpx

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000/api/v1"


async def run_tests():
    print("==================================================")
    print("TASK 13 — BACKEND PROFILE INTEGRATION TESTS")
    print("==================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Unauthenticated checks
        r_unauth_get = await client.get(f"{BASE_URL}/profile")
        assert r_unauth_get.status_code == 401, f"Expected 401 for unauth GET, got {r_unauth_get.status_code}"

        r_unauth_patch = await client.patch(f"{BASE_URL}/profile", json={"headline": "Hacker"})
        assert r_unauth_patch.status_code == 401, f"Expected 401 for unauth PATCH, got {r_unauth_patch.status_code}"
        print("[PASS] 1. Unauthenticated requests to /profile return 401 Unauthorized")

        # 2. Setup User A & User B
        email_a = f"candidate_a_{uuid.uuid4().hex[:6]}@example.com"
        email_b = f"candidate_b_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "ProductionPassword123!"

        reg_a = await client.post(f"{BASE_URL}/auth/register", json={"email": email_a, "password": pwd, "full_name": "Alice Developer"})
        assert reg_a.status_code == 201
        login_a = await client.post(f"{BASE_URL}/auth/login", json={"email": email_a, "password": pwd})
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        reg_b = await client.post(f"{BASE_URL}/auth/register", json={"email": email_b, "password": pwd, "full_name": "Bob Architect"})
        assert reg_b.status_code == 201
        login_b = await client.post(f"{BASE_URL}/auth/login", json={"email": email_b, "password": pwd})
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("[PASS] 2. User A and User B successfully registered and authenticated")

        # 3. Fetch Initial Profile for User A
        res_a = await client.get(f"{BASE_URL}/profile", headers=headers_a)
        assert res_a.status_code == 200, f"Expected 200, got {res_a.status_code}"
        data_a = res_a.json()

        assert "profile" in data_a
        assert "account" in data_a
        assert "practice_summary" in data_a
        assert "achievement_summary" in data_a
        assert "interview_summary" in data_a
        assert "resume_status" in data_a

        assert data_a["profile"]["full_name"] == "Alice Developer"
        assert data_a["profile"]["email"] == email_a
        assert data_a["account"]["email"] == email_a
        assert data_a["practice_summary"]["questions_solved"] == 0
        assert data_a["practice_summary"]["total_xp"] == 0
        assert data_a["achievement_summary"]["unlocked_count"] == 0
        assert data_a["interview_summary"]["completed_interviews"] == 0
        assert data_a["resume_status"]["has_resume"] is False
        print("[PASS] 3. Authenticated GET /profile returns authoritative structure with accurate real zero-state metrics")

        # 4. Profile Update for User A
        update_payload = {
            "full_name": "Alice M. Developer",
            "headline": "Full-Stack AI Engineer",
            "bio": "Passionate about distributed systems, LLMs, and real-time platforms.",
            "college": "Stanford University",
            "degree": "B.S. Computer Science",
            "graduation_year": 2024,
            "target_role": "Senior Software Engineer",
            "experience_level": "Mid-Level",
            "location": "San Francisco, CA",
            "phone": "+1 555-0199",
            "github_url": "https://github.com/alice-dev",
            "linkedin_url": "https://linkedin.com/in/alice-dev",
            "portfolio_url": "https://alice.dev",
            "avatar_url": "https://alice.dev/avatar.jpg"
        }
        patch_res = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json=update_payload)
        assert patch_res.status_code == 200, f"Expected 200, got {patch_res.status_code}: {patch_res.text}"
        patched_data = patch_res.json()["profile"]

        assert patched_data["full_name"] == "Alice M. Developer"
        assert patched_data["headline"] == "Full-Stack AI Engineer"
        assert patched_data["bio"] == "Passionate about distributed systems, LLMs, and real-time platforms."
        assert patched_data["college"] == "Stanford University"
        assert patched_data["degree"] == "B.S. Computer Science"
        assert patched_data["graduation_year"] == 2024
        assert patched_data["target_role"] == "Senior Software Engineer"
        assert patched_data["experience_level"] == "Mid-Level"
        assert patched_data["location"] == "San Francisco, CA"
        assert patched_data["phone"] == "+1 555-0199"
        assert patched_data["github_url"] == "https://github.com/alice-dev"
        assert patched_data["linkedin_url"] == "https://linkedin.com/in/alice-dev"
        assert patched_data["portfolio_url"] == "https://alice.dev"
        assert patched_data["avatar_url"] == "https://alice.dev/avatar.jpg"
        print("[PASS] 4. Profile PATCH correctly updates and persists all allowed profile fields")

        # 5. Validation Rejections: Invalid URLs and graduation years
        bad_url_res = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"github_url": "invalid-url-not-http"})
        assert bad_url_res.status_code == 422, f"Expected 422 for invalid URL, got {bad_url_res.status_code}"

        bad_year_res = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"graduation_year": 1950})
        assert bad_year_res.status_code == 422, f"Expected 422 for graduation year 1950, got {bad_year_res.status_code}"

        bad_year_future = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"graduation_year": 2099})
        assert bad_year_future.status_code == 422, f"Expected 422 for graduation year 2099, got {bad_year_future.status_code}"
        print("[PASS] 5. Validation correctly rejects invalid URLs and out-of-range graduation years")

        # 6. Protected Fields Cannot Be Manipulated
        # Extra fields are forbidden by schema (extra="forbid")
        tamper_xp = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"total_xp": 999999})
        assert tamper_xp.status_code == 422, f"Expected 422 on total_xp tampering, got {tamper_xp.status_code}"

        tamper_level = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"current_level": 50})
        assert tamper_level.status_code == 422, f"Expected 422 on current_level tampering, got {tamper_level.status_code}"

        tamper_user_id = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"user_id": str(uuid.uuid4())})
        assert tamper_user_id.status_code == 422, f"Expected 422 on user_id tampering, got {tamper_user_id.status_code}"

        tamper_email = await client.patch(f"{BASE_URL}/profile", headers=headers_a, json={"email": "hacked@example.com"})
        assert tamper_email.status_code == 422, f"Expected 422 on email tampering, got {tamper_email.status_code}"
        print("[PASS] 6. Protected fields (total_xp, current_level, user_id, email) strictly forbidden from client manipulation")

        # 7. Practice and Gamification Integration: Real data reflection
        # Solve a practice question for User A
        q_list_res = await client.get(f"{BASE_URL}/practice/questions?limit=2", headers=headers_a)
        assert q_list_res.status_code == 200
        questions = q_list_res.json()["questions"]
        q1 = questions[0]

        solve_res = await client.post(
            f"{BASE_URL}/practice/questions/{q1['id']}/solve",
            headers=headers_a,
            json={"solved": True, "answer": "Demonstrating thorough mastery of the problem and technical correctness."}
        )
        assert solve_res.status_code == 200

        # Now re-fetch profile for User A
        refetched_a = await client.get(f"{BASE_URL}/profile", headers=headers_a)
        assert refetched_a.status_code == 200
        data_a_updated = refetched_a.json()
        assert data_a_updated["practice_summary"]["questions_solved"] >= 1
        assert data_a_updated["practice_summary"]["total_xp"] > 0
        assert len(data_a_updated["practice_summary"]["technologies_practiced"]) >= 1
        tech_practiced = data_a_updated["practice_summary"]["technologies_practiced"][0]
        assert tech_practiced["solved"] >= 1
        print(f"[PASS] 7. Practice integration verified: Solved {data_a_updated['practice_summary']['questions_solved']} questions, XP {data_a_updated['practice_summary']['total_xp']}, Tech: {tech_practiced['technology']}")

        # 8. User Isolation Check
        # User B fetches profile
        res_b = await client.get(f"{BASE_URL}/profile", headers=headers_b)
        assert res_b.status_code == 200
        data_b = res_b.json()

        # User B must NOT have User A's data
        assert data_b["profile"]["full_name"] == "Bob Architect"
        assert data_b["profile"]["email"] == email_b
        assert data_b["profile"]["headline"] is None
        assert data_b["practice_summary"]["questions_solved"] == 0
        assert data_b["practice_summary"]["total_xp"] == 0
        assert len(data_b["practice_summary"]["technologies_practiced"]) == 0

        # User B updates their profile
        patch_b = await client.patch(
            f"{BASE_URL}/profile",
            headers=headers_b,
            json={
                "headline": "Lead Systems Architect",
                "college": "MIT",
                "degree": "M.S. EECS",
                "graduation_year": 2020,
            }
        )
        assert patch_b.status_code == 200
        assert patch_b.json()["profile"]["headline"] == "Lead Systems Architect"

        # User A refetches profile to ensure no pollution from User B
        refetched_a2 = await client.get(f"{BASE_URL}/profile", headers=headers_a)
        assert refetched_a2.json()["profile"]["headline"] == "Full-Stack AI Engineer"
        assert refetched_a2.json()["profile"]["college"] == "Stanford University"
        print("[PASS] 8. User isolation verified: User A and User B profiles and statistics are completely isolated")

        # 9. Persistence check across re-login
        login_a2 = await client.post(f"{BASE_URL}/auth/login", json={"email": email_a, "password": pwd})
        token_a2 = login_a2.json()["access_token"]
        headers_a2 = {"Authorization": f"Bearer {token_a2}"}
        relog_res = await client.get(f"{BASE_URL}/profile", headers=headers_a2)
        assert relog_res.status_code == 200
        assert relog_res.json()["profile"]["full_name"] == "Alice M. Developer"
        assert relog_res.json()["profile"]["headline"] == "Full-Stack AI Engineer"
        assert relog_res.json()["profile"]["graduation_year"] == 2024
        print("[PASS] 9. Persistence verified across re-login session")

    print("==================================================")
    print("ALL TASK 13 BACKEND PROFILE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_tests())
