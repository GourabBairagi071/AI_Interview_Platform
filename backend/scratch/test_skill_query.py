import asyncio
import re
import uuid
from sqlalchemy import select, and_, or_, func
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.learning.model import SkillPerformance

async def test_skill_matching():
    async with AsyncSessionLocal() as db:
        # Create test users with various skill formats
        u1 = User(email=f"cand_sk1_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        u2 = User(email=f"cand_sk2_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        u3 = User(email=f"cand_sk3_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        u4 = User(email=f"cand_sk4_{uuid.uuid4().hex[:6]}@example.com", role="CANDIDATE", is_active=True)
        db.add_all([u1, u2, u3, u4])
        await db.commit()
        for u in [u1, u2, u3, u4]:
            await db.refresh(u)

        p1 = UserProfile(user_id=u1.id, skills='["Python", "FastAPI"]')
        p2 = UserProfile(user_id=u2.id, skills='["Java", "Spring Boot"]')
        p3 = UserProfile(user_id=u3.id, skills='["JavaScript", "Node.js"]')
        p4 = UserProfile(user_id=u4.id, skills="Python, SQL, Machine Learning")
        db.add_all([p1, p2, p3, p4])
        await db.commit()

        def build_skill_query(target_skill: str):
            if not target_skill or not target_skill.strip():
                return select(User.id).where(User.id == None)  # Returns empty
            
            clean = target_skill.strip()
            # Escape regex special chars
            safe_regex = rf"\y{re.escape(clean)}\y"

            # Query matching UserProfile.skills via regex word boundary OR exact JSON containment OR SkillPerformance
            return (
                select(User.id)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .where(
                    and_(
                        User.role == "CANDIDATE",
                        User.is_active.is_(True),
                        or_(
                            UserProfile.skills.op("~*")(safe_regex),
                            User.id.in_(
                                select(SkillPerformance.user_id).where(
                                    SkillPerformance.canonical_skill.ilike(f"%{clean}%")
                                )
                            )
                        )
                    )
                )
            )

        # Test 1: Python
        q1 = build_skill_query("Python")
        r1 = list((await db.execute(q1)).scalars().all())
        print("Target 'Python':", len(r1), "matched.")
        assert u1.id in r1 and u4.id in r1, "u1 and u4 should match Python"
        assert u2.id not in r1 and u3.id not in r1, "u2 and u3 should NOT match Python"

        # Test 2: Java (must NOT match JavaScript)
        q2 = build_skill_query("Java")
        r2 = list((await db.execute(q2)).scalars().all())
        print("Target 'Java':", len(r2), "matched.")
        assert u2.id in r2, "u2 should match Java"
        assert u3.id not in r2, "u3 (JavaScript) should NOT match Java!"
        assert u1.id not in r2 and u4.id not in r2, "u1 and u4 should NOT match Java"

        # Test 3: FastAPI
        q3 = build_skill_query("FastAPI")
        r3 = list((await db.execute(q3)).scalars().all())
        print("Target 'FastAPI':", len(r3), "matched.")
        assert u1.id in r3, "u1 should match FastAPI"
        assert u2.id not in r3 and u3.id not in r3, "u2 and u3 should NOT match FastAPI"

        # Test 4: Empty string
        q4 = build_skill_query("")
        r4 = list((await db.execute(q4)).scalars().all())
        print("Target '':", len(r4), "matched.")
        assert len(r4) == 0, "Empty skill target must return 0 candidates!"

        print("Skill query test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_skill_matching())
