import asyncio
import uuid
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.admin.model import Company
from app.modules.assignments.service import AssignmentService

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_defect_04_fix():
    print("=== TESTING DEFECT-04 (COMPANY TARGETING) FIX ===")
    async with AsyncSessionLocal() as db:
        # Create test company A and company B
        comp_a_name = f"TestCorp Alpha {uuid.uuid4().hex[:6]}"
        comp_b_name = f"TestCorp Beta {uuid.uuid4().hex[:6]}"
        
        comp_a = Company(name=comp_a_name, industry="Tech")
        comp_b = Company(name=comp_b_name, industry="Finance")
        db.add(comp_a)
        db.add(comp_b)
        await db.commit()
        await db.refresh(comp_a)
        await db.refresh(comp_b)

        # Create Candidate A (belonging to Company A) and Candidate B (belonging to Company B)
        cand_a_email = f"cand_comp_a_{uuid.uuid4().hex[:6]}@example.com"
        cand_b_email = f"cand_comp_b_{uuid.uuid4().hex[:6]}@example.com"

        user_a = User(email=cand_a_email, role="CANDIDATE", is_active=True, is_verified=True)
        user_b = User(email=cand_b_email, role="CANDIDATE", is_active=True, is_verified=True)
        db.add(user_a)
        db.add(user_b)
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)

        profile_a = UserProfile(user_id=user_a.id, headline=f"Engineer at {comp_a_name}")
        profile_b = UserProfile(user_id=user_b.id, headline=f"Analyst at {comp_b_name}")
        db.add(profile_a)
        db.add(profile_b)
        await db.commit()

        # Test Case 1: Missing company target -> must return [] (empty list)
        empty_res = await AssignmentService.resolve_candidate_recipients(
            db=db,
            target_type="COMPANY",
            target_filter={}
        )
        print(f"Test Case 1 (Missing company): returned {len(empty_res)} candidates.")
        assert empty_res == [], f"Expected [], got {empty_res}"

        # Test Case 2: Target Company A by name
        comp_a_res = await AssignmentService.resolve_candidate_recipients(
            db=db,
            target_type="COMPANY",
            target_filter={"company_name": comp_a_name}
        )
        print(f"Test Case 2 (Company A name): resolved {len(comp_a_res)} candidates.")
        assert user_a.id in comp_a_res, "Candidate A should be resolved for Company A"
        assert user_b.id not in comp_a_res, "Candidate B should NOT be resolved for Company A"

        # Test Case 3: Target Company A by UUID
        comp_a_uuid_res = await AssignmentService.resolve_candidate_recipients(
            db=db,
            target_type="COMPANY",
            target_filter={"company_id": str(comp_a.id)}
        )
        print(f"Test Case 3 (Company A UUID): resolved {len(comp_a_uuid_res)} candidates.")
        assert user_a.id in comp_a_uuid_res, "Candidate A should be resolved for Company A UUID"
        assert user_b.id not in comp_a_uuid_res, "Candidate B should NOT be resolved for Company A UUID"

        # Test Case 4: Target Company with explicit candidate_ids
        explicit_res = await AssignmentService.resolve_candidate_recipients(
            db=db,
            target_type="COMPANY",
            target_filter={"company_name": comp_a_name, "candidate_ids": [str(user_a.id)]}
        )
        print(f"Test Case 4 (Explicit candidate_ids): resolved {len(explicit_res)} candidates.")
        assert explicit_res == [user_a.id], f"Expected [{user_a.id}], got {explicit_res}"

        # Clean up test users & profiles
        print("SUCCESS: DEFECT-04 FIX VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_04_fix())
