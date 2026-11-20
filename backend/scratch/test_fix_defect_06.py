import asyncio
import uuid
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.resume.model import Resume
from app.modules.interview.model import Interview
from app.modules.admin.service import AdminService

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_defect_06_fix():
    print("=== TESTING DEFECT-06 (DASHBOARD SUMMARY RESUME ATTRIBUTE) FIX ===")

    # 1. Test Candidate WITH Resume
    async with AsyncSessionLocal() as db:
        user_a = User(email=f"cand_dash_with_res_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True, is_verified=True)
        db.add(user_a)
        await db.commit()
        await db.refresh(user_a)

        resume_a = Resume(
            user_id=user_a.id,
            filename="my_resume.pdf",
            file_url="https://example.com/resumes/my_resume.pdf",
        )
        db.add(resume_a)
        await db.commit()

        interview_a = Interview(
            user_id=user_a.id,
            job_role="Senior Backend Engineer",
            difficulty="Hard",
            status="completed",
        )
        db.add(interview_a)
        await db.commit()

        user_a_id = user_a.id

    # Execute service method directly
    async with AsyncSessionLocal() as db:
        summary_a = await AdminService.get_candidate_dashboard_summary(db, user_a_id)
        print("Candidate WITH Resume summary fetched successfully!")
        assert "config" in summary_a
        assert "featured" in summary_a
        assert "ats" in summary_a
        assert summary_a["ats"]["resume_id"] is not None
        assert summary_a["recent_interview"] is not None
        assert summary_a["recent_interview"]["job_role"] == "Senior Backend Engineer"

    # 2. Test Candidate WITHOUT Resume (Partial / Empty Data)
    async with AsyncSessionLocal() as db:
        user_b = User(email=f"cand_dash_no_res_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True, is_verified=True)
        db.add(user_b)
        await db.commit()
        await db.refresh(user_b)
        user_b_id = user_b.id

    async with AsyncSessionLocal() as db:
        summary_b = await AdminService.get_candidate_dashboard_summary(db, user_b_id)
        print("Candidate WITHOUT Resume summary fetched successfully!")
        assert summary_b["ats"]["resume_id"] is None
        assert summary_b["recent_interview"] is None

    # 3. Test API HTTP Endpoints (/dashboard/summary, /dashboard/config, /dashboard/featured)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Unauthenticated request -> should return 401
        res_unauth = await client.get("/dashboard/summary")
        print(f"Unauthenticated /dashboard/summary -> status {res_unauth.status_code}")
        assert res_unauth.status_code in [401, 403]

        # Dashboard Config (Public / Candidate)
        res_config = await client.get("/dashboard/config")
        print(f"/dashboard/config -> status {res_config.status_code}")
        assert res_config.status_code == 200

        # Dashboard Featured
        res_feat = await client.get("/dashboard/featured")
        print(f"/dashboard/featured -> status {res_feat.status_code}")
        assert res_feat.status_code == 200

    print("SUCCESS: DEFECT-06 FIX VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_06_fix())
