import asyncio
import uuid
from datetime import timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from app.modules.admin.model import Company
from app.modules.payments.model import UserSubscription, SubscriptionPlan
from app.modules.assignments.service import AssignmentService, utc_now

async def test_defect_03_fix():
    print("=== TESTING DEFECT-03 (FREE SUBSCRIPTION TARGETING) FIX ===")

    async with AsyncSessionLocal() as db:
        now = utc_now()

        # 1. Fetch or create Pro and Premium subscription plans
        pro_plan_res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name.ilike("%PRO%")))
        pro_plan = pro_plan_res.scalars().first()
        if not pro_plan:
            pro_plan = SubscriptionPlan(name="Pro Tier", slug=f"pro_{uuid.uuid4().hex[:4]}", price=49900)
            db.add(pro_plan)
            await db.commit()
            await db.refresh(pro_plan)

        prem_plan_res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name.ilike("%PREMIUM%")))
        prem_plan = prem_plan_res.scalars().first()
        if not prem_plan:
            prem_plan = SubscriptionPlan(name="Premium Tier", slug=f"premium_{uuid.uuid4().hex[:4]}", price=99900)
            db.add(prem_plan)
            await db.commit()
            await db.refresh(prem_plan)

        free_plan_res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name.ilike("%FREE%")))
        free_plan = free_plan_res.scalars().first()
        if not free_plan:
            free_plan = SubscriptionPlan(name="Free Plan", slug=f"free_{uuid.uuid4().hex[:4]}", price=0)
            db.add(free_plan)
            await db.commit()
            await db.refresh(free_plan)

        # Create candidates representing distinct subscription states
        # Candidate A: NO subscription row
        u_no_sub = User(email=f"cand_nosub_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        # Candidate B: Explicit active FREE subscription row
        u_free_sub = User(email=f"cand_freesub_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        # Candidate C: Active PRO subscription row
        u_pro_sub = User(email=f"cand_prosub_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        # Candidate D: Active PREMIUM subscription row
        u_prem_sub = User(email=f"cand_premsub_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        # Candidate E: Expired PRO subscription row
        u_exp_sub = User(email=f"cand_expsub_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)

        db.add_all([u_no_sub, u_free_sub, u_pro_sub, u_prem_sub, u_exp_sub])
        await db.commit()

        for u in [u_no_sub, u_free_sub, u_pro_sub, u_prem_sub, u_exp_sub]:
            await db.refresh(u)

        # Add explicit subscription rows
        sub_free = UserSubscription(user_id=u_free_sub.id, plan_id=free_plan.id, status="active")
        sub_pro = UserSubscription(user_id=u_pro_sub.id, plan_id=pro_plan.id, status="active", expires_at=now + timedelta(days=30))
        sub_prem = UserSubscription(user_id=u_prem_sub.id, plan_id=prem_plan.id, status="active", expires_at=now + timedelta(days=30))
        sub_exp = UserSubscription(user_id=u_exp_sub.id, plan_id=pro_plan.id, status="active", expires_at=now - timedelta(days=5))

        db.add_all([sub_free, sub_pro, sub_prem, sub_exp])
        await db.commit()

        # -----------------------------------------------------------
        # TEST 1: FREE Targeting
        # -----------------------------------------------------------
        res_free = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SUBSCRIPTION_TIER", target_filter={"tier": "FREE"}
        )
        print(f"1. Target 'FREE': resolved {len(res_free)} candidates.")
        assert u_no_sub.id in res_free, "Candidate A (NO sub row) MUST be included in FREE targeting"
        assert u_free_sub.id in res_free, "Candidate B (explicit FREE row) MUST be included in FREE targeting"
        assert u_exp_sub.id in res_free, "Candidate E (expired PRO sub) MUST be included in FREE targeting"
        assert u_pro_sub.id not in res_free, "Candidate C (active PRO) MUST be EXCLUDED from FREE targeting"
        assert u_prem_sub.id not in res_free, "Candidate D (active PREMIUM) MUST be EXCLUDED from FREE targeting"

        # -----------------------------------------------------------
        # TEST 2: PRO Targeting
        # -----------------------------------------------------------
        res_pro = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SUBSCRIPTION_TIER", target_filter={"tier": "PRO"}
        )
        print(f"2. Target 'PRO': resolved {len(res_pro)} candidates.")
        assert u_pro_sub.id in res_pro, "Candidate C (active PRO) MUST be included in PRO targeting"
        assert u_no_sub.id not in res_pro and u_free_sub.id not in res_pro, "FREE candidates MUST be EXCLUDED from PRO targeting"
        assert u_exp_sub.id not in res_pro, "Expired PRO candidate MUST be EXCLUDED from PRO targeting"

        # -----------------------------------------------------------
        # TEST 3: PREMIUM Targeting
        # -----------------------------------------------------------
        res_prem = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SUBSCRIPTION_TIER", target_filter={"tier": "PREMIUM"}
        )
        print(f"3. Target 'PREMIUM': resolved {len(res_prem)} candidates.")
        assert u_prem_sub.id in res_prem, "Candidate D (active PREMIUM) MUST be included in PREMIUM targeting"
        assert u_pro_sub.id not in res_prem and u_free_sub.id not in res_prem

        # -----------------------------------------------------------
        # TEST 4: Invalid Tier
        # -----------------------------------------------------------
        res_invalid = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SUBSCRIPTION_TIER", target_filter={"tier": "INVALID_VIP_TIER"}
        )
        print(f"4. Target 'INVALID_VIP_TIER': resolved {len(res_invalid)} candidates.")
        assert res_invalid == [], "Invalid tier MUST return []"

        # -----------------------------------------------------------
        # TEST 5: Empty Tier
        # -----------------------------------------------------------
        res_empty = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SUBSCRIPTION_TIER", target_filter={"tier": ""}
        )
        print(f"5. Target '' (empty): resolved {len(res_empty)} candidates.")
        assert res_empty == [], "Empty tier MUST return [] (no fallthrough to ALL)"

        # -----------------------------------------------------------
        # TARGETING REGRESSION REVIEW
        # -----------------------------------------------------------
        print("\n--- ALL TARGETING MECHANISMS REGRESSION REVIEW ---")

        # SKILL (verifying DEFECT-02 remains fixed)
        res_sk = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="SKILL", target_filter={"skill": "Python"}
        )
        assert isinstance(res_sk, list), "SKILL regression check failed"

        # COMPANY (verifying DEFECT-04 remains fixed)
        res_comp_empty = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="COMPANY", target_filter={}
        )
        assert res_comp_empty == [], "COMPANY empty fallback regression check failed"

        # ALL
        res_all = await AssignmentService.resolve_candidate_recipients(
            db=db, target_type="ALL", target_filter={}
        )
        assert len(res_all) >= 5, "ALL targeting check failed"

        print("SUCCESS: DEFECT-03 FIX AND FULL TARGETING REGRESSION VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_03_fix())
