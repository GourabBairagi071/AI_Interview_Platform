import asyncio
import uuid
import httpx
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.assignments.model import CandidateAssignment, CandidateAssignmentProgress
from app.modules.assignments.service import AssignmentService
from app.modules.learning.model import SkillPerformance
from app.modules.notifications.model import Notification

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_defect_05_concurrency():
    print("=== TESTING DEFECT-05 (CONCURRENT SUBMISSION) FIX ===")
    
    # 1. Create a candidate user & assignment in DB
    async with AsyncSessionLocal() as db:
        user_email = f"cand_defect5_{uuid.uuid4().hex[:6]}@example.com"
        cand_user = User(email=user_email, role="CANDIDATE", is_active=True, is_verified=True)
        db.add(cand_user)
        await db.commit()
        await db.refresh(cand_user)

        profile = UserProfile(user_id=cand_user.id, skills="Python, FastApi")
        db.add(profile)
        await db.commit()

        # Create test assignment
        assignment = CandidateAssignment(
            title=f"Concurrency Test Task {uuid.uuid4().hex[:6]}",
            assignment_type="CODING_PROBLEM",
            target_type="INDIVIDUAL",
            priority="HIGH",
            attempt_limit=1,
            created_by_admin_id=cand_user.id,
            status="ASSIGNED",
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        # Create candidate progress row
        progress = CandidateAssignmentProgress(
            assignment_id=assignment.id,
            candidate_id=cand_user.id,
            status="IN_PROGRESS",
            progress_percent=50.0,
            attempt_count=1,
        )
        db.add(progress)
        await db.commit()

        cand_id = cand_user.id
        ass_id = assignment.id

    print(f"Created candidate {cand_id} and assignment {ass_id}")

    # Log in or test via direct Service layer or HTTP concurrent calls
    # Let's test direct concurrent Service execution first, then HTTP requests!

    # Test A: 2 Simultaneous Submissions
    print("\n--- Test A: 2 Simultaneous Submissions ---")
    async def submit_worker(score_val: float):
        async with AsyncSessionLocal() as session:
            class DummyData:
                score = score_val
                submission_ref_id = None
                submission_data = {"test": "concurrency"}
            return await AssignmentService.submit_candidate_assignment(
                db=session,
                assignment_id=ass_id,
                candidate_id=cand_id,
                data=DummyData()
            )

    results_a = await asyncio.gather(submit_worker(85.0), submit_worker(90.0), return_exceptions=True)
    
    # Check zero exceptions bubbled up
    for idx, r in enumerate(results_a):
        print(f"Worker {idx+1} result: {r}")
        assert not isinstance(r, Exception), f"Worker {idx+1} raised exception: {r}"
        assert r is not None
        assert r["status"] == "COMPLETED"

    # Verify Database State after Test A
    async with AsyncSessionLocal() as db:
        prog_res = await db.execute(
            select(CandidateAssignmentProgress).where(
                CandidateAssignmentProgress.assignment_id == ass_id,
                CandidateAssignmentProgress.candidate_id == cand_id,
            )
        )
        final_p = prog_res.scalar_one()
        print(f"Final Progress Row -> status: {final_p.status}, score: {final_p.score}, attempts: {final_p.attempt_count}")
        assert final_p.status == "COMPLETED"
        assert final_p.progress_percent == 100.0

        # Check skill performance
        sp_res = await db.execute(select(SkillPerformance).where(SkillPerformance.user_id == cand_id))
        sps = sp_res.scalars().all()
        print(f"Skill Performances synced -> count: {len(sps)}")
        canonical_names = [sp.canonical_skill for sp in sps]
        assert len(canonical_names) == len(set(canonical_names)), "Duplicate skill records found!"

        # Check notifications
        notif_res = await db.execute(select(Notification).where(Notification.user_id == cand_id))
        notifs = notif_res.scalars().all()
        print(f"Notifications generated -> count: {len(notifs)}")
        assert len(notifs) >= 1, "Completion notification should be generated"

    # Test B: 3 Simultaneous Submissions on a New Task
    print("\n--- Test B: 3 Simultaneous Submissions ---")
    async with AsyncSessionLocal() as db:
        ass_b = CandidateAssignment(
            title=f"Concurrency Test Task B {uuid.uuid4().hex[:6]}",
            assignment_type="PRACTICE_SET",
            target_type="INDIVIDUAL",
            attempt_limit=1,
            created_by_admin_id=cand_id,
            status="ASSIGNED",
        )
        db.add(ass_b)
        await db.commit()
        await db.refresh(ass_b)

        prog_b = CandidateAssignmentProgress(
            assignment_id=ass_b.id,
            candidate_id=cand_id,
            status="IN_PROGRESS",
            progress_percent=10.0,
            attempt_count=1,
        )
        db.add(prog_b)
        await db.commit()
        ass_b_id = ass_b.id

    async def submit_worker_b(score_val: float):
        async with AsyncSessionLocal() as session:
            class DummyData:
                score = score_val
                submission_ref_id = None
                submission_data = {"test": "concurrency_b"}
            return await AssignmentService.submit_candidate_assignment(
                db=session,
                assignment_id=ass_b_id,
                candidate_id=cand_id,
                data=DummyData()
            )

    results_b = await asyncio.gather(
        submit_worker_b(75.0),
        submit_worker_b(80.0),
        submit_worker_b(85.0),
        return_exceptions=True
    )

    for idx, r in enumerate(results_b):
        print(f"Worker B{idx+1} result: {r}")
        assert not isinstance(r, Exception), f"Worker B{idx+1} raised exception: {r}"
        assert r["status"] == "COMPLETED"

    # Test C: Duplicate Submit on already completed assignment
    print("\n--- Test C: Duplicate Submit on Already Completed Assignment ---")
    async with AsyncSessionLocal() as session:
        class DummyData:
            score = 99.0
            submission_ref_id = None
            submission_data = {"test": "dup"}
        dup_res = await AssignmentService.submit_candidate_assignment(
            db=session,
            assignment_id=ass_b_id,
            candidate_id=cand_id,
            data=DummyData()
        )
        print(f"Duplicate submission result: {dup_res}")
        assert dup_res["status"] == "COMPLETED"

    print("SUCCESS: DEFECT-05 FIX VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_05_concurrency())
