import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.admin.model import Company
from app.modules.assignments.service import AssignmentService

async def test_defect_02_fix():
    print("=== TESTING DEFECT-02 (SKILL TARGETING) FIX ===")
    
    async with AsyncSessionLocal() as db:
        # Create test candidates with distinct skill formats
        cand_py_email = f"cand_py_{uuid.uuid4().hex[:6]}@example.com"
        cand_java_email = f"cand_java_{uuid.uuid4().hex[:6]}@example.com"
        cand_sql_email = f"cand_sql_{uuid.uuid4().hex[:6]}@example.com"

        u_py = User(email=cand_py_email, role="CANDIDATE", is_active=True, is_verified=True)
        u_java = User(email=cand_java_email, role="CANDIDATE", is_active=True, is_verified=True)
        u_sql = User(email=cand_sql_email, role="CANDIDATE", is_active=True, is_verified=True)

        db.add_all([u_py, u_java, u_sql])
        await db.commit()
        for u in [u_py, u_java, u_sql]:
            await db.refresh(u)

        # Profile Py: JSON array ["Python", "FastAPI"]
        p_py = UserProfile(user_id=u_py.id, skills='["Python", "FastAPI"]')
        # Profile Java: JSON array ["Java", "Spring Boot"]
        p_java = UserProfile(user_id=u_java.id, skills='["Java", "Spring Boot"]')
        # Profile SQL: String format "PostgreSQL, SQL, Machine Learning"
        p_sql = UserProfile(user_id=u_sql.id, skills="PostgreSQL, SQL, Machine Learning")

        db.add_all([p_py, p_java, p_sql])
        await db.commit()

        # 1. Target Skill: Python
        res_py = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "Python"}
        )
        print(f"1. Target 'Python': resolved {len(res_py)} candidates.")
        assert u_py.id in res_py, "Candidate Py should match 'Python'"
        assert u_java.id not in res_py, "Candidate Java should NOT match 'Python'"

        # 2. Target Skill: FastAPI
        res_api = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "FastAPI"}
        )
        print(f"2. Target 'FastAPI': resolved {len(res_api)} candidates.")
        assert u_py.id in res_api, "Candidate Py should match 'FastAPI'"
        assert u_java.id not in res_api, "Candidate Java should NOT match 'FastAPI'"

        # 3. Target Skill: SQL
        res_sql = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "SQL"}
        )
        print(f"3. Target 'SQL': resolved {len(res_sql)} candidates.")
        assert u_sql.id in res_sql, "Candidate SQL should match 'SQL'"
        assert u_java.id not in res_sql, "Candidate Java should NOT match 'SQL'"

        # 4. Case variation: "python" (lowercase)
        res_lower = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "python"}
        )
        print(f"4. Target 'python' (lowercase): resolved {len(res_lower)} candidates.")
        assert u_py.id in res_lower, "Candidate Py should match lowercase 'python'"

        # 5. Nonexistent Skill: "QuantumComputing"
        res_none = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "QuantumComputing"}
        )
        print(f"5. Target 'QuantumComputing': resolved {len(res_none)} candidates.")
        assert u_py.id not in res_none and u_java.id not in res_none and u_sql.id not in res_none

        # 6. Empty Skill: ""
        res_empty = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": ""}
        )
        print(f"6. Target '' (empty): resolved {len(res_empty)} candidates.")
        assert res_empty == [], f"Empty skill target must return [], got {res_empty}"

        # 7. Word boundary check: "Java" must NOT match "JavaScript"
        u_js = User(email=f"cand_js_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        db.add(u_js)
        await db.commit()
        await db.refresh(u_js)
        p_js = UserProfile(user_id=u_js.id, skills='["JavaScript", "React"]')
        db.add(p_js)
        await db.commit()

        res_java = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "Java"}
        )
        print(f"7. Target 'Java': resolved {len(res_java)} candidates.")
        assert u_java.id in res_java, "Candidate Java should match 'Java'"
        assert u_js.id not in res_java, "Candidate JS ('JavaScript') must NOT match 'Java'!"

        # 8. Regression Verification for All 8 Targeting Mechanisms
        print("\n--- TARGETING REGRESSION VERIFICATION ---")

        # INDIVIDUAL
        r_ind = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="INDIVIDUAL", target_filter={"candidate_id": str(u_py.id)}
        )
        assert r_ind == [u_py.id], "INDIVIDUAL targeting regression failed"

        # GROUP
        r_grp = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="GROUP", target_filter={"candidate_ids": [str(u_py.id), str(u_java.id)]}
        )
        assert u_py.id in r_grp and u_java.id in r_grp, "GROUP targeting regression failed"

        # ROLE
        r_role = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="ROLE", target_filter={"role": "CANDIDATE"}
        )
        assert len(r_role) >= 3, "ROLE targeting regression failed"

        # COMPANY (Verifying DEFECT-04 remains fixed!)
        comp = Company(name=f"RegressionCorp_{uuid.uuid4().hex[:6]}")
        db.add(comp)
        await db.commit()
        await db.refresh(comp)

        r_comp_empty = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="COMPANY", target_filter={}
        )
        assert r_comp_empty == [], "COMPANY targeting empty fallback regression failed (must return [])"

        # ALL
        r_all = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="ALL", target_filter={}
        )
        assert len(r_all) >= 4, "ALL targeting regression failed"

        print("SUCCESS: DEFECT-02 FIX AND TARGETING REGRESSION VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_02_fix())
