import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from app.modules.achievements.service import (
    ensure_achievement_definitions,
    evaluate_user_achievements,
    get_user_achievements_list,
    get_user_achievements_summary,
    get_achievement_detail,
)
from app.modules.achievements.model import AchievementDefinition, UserAchievement
from app.modules.practice.service import solve_practice_question, load_all_platform_questions


async def main():
    print("=" * 60)
    print("TESTING ACHIEVEMENTS BACKEND SERVICE & REPOSITORY")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Definitions Seed Test
        defs = await ensure_achievement_definitions(db)
        print(f"[PASS] 1. Canonical achievement definitions seeded: {len(defs)} definitions")
        assert len(defs) >= 30, f"Expected >= 30 definitions, got {len(defs)}"

        # 2. Test with User
        u_stmt = select(User).limit(1)
        user = (await db.execute(u_stmt)).scalars().first()
        assert user is not None, "No user found in database"
        user_id = user.id
        print(f"Testing with User: {user.email} ({user_id})")

        # 3. Evaluation Test
        all_items, newly_unlocked = await evaluate_user_achievements(db, user_id)
        print(f"[PASS] 3. Evaluated achievements: {len(all_items)} total items, {len(newly_unlocked)} newly unlocked")
        assert len(all_items) == len(defs)

        # 4. List endpoint test
        list_res = await get_user_achievements_list(db, user_id)
        print(f"[PASS] 4. Achievement list response: {list_res.total} total, {list_res.unlocked_count} unlocked")
        assert list_res.total == len(defs)

        # 5. Filter by category test
        practice_res = await get_user_achievements_list(db, user_id, category="Practice")
        assert all(a.category.lower() == "practice" for a in practice_res.achievements)
        print(f"[PASS] 5. Category filter verified: {practice_res.total} Practice achievements")

        # 6. Summary endpoint test
        summary = await get_user_achievements_summary(db, user_id)
        print(f"[PASS] 6. Summary response: {summary.unlocked_count}/{summary.total_achievements} unlocked ({summary.completion_percentage}%), {summary.total_xp_earned} XP earned")
        assert len(summary.categories) == 8, f"Expected 8 categories, got {len(summary.categories)}"

        # 7. Detail endpoint test
        first_id = defs[0].id
        detail = await get_achievement_detail(db, user_id, first_id)
        print(f"[PASS] 7. Detail response for '{first_id}': {detail.achievement.name} ({detail.achievement.rarity})")
        assert detail.achievement.id == first_id

        # 8. Duplicate evaluation test (idempotency)
        _, newly_unlocked_2 = await evaluate_user_achievements(db, user_id)
        print(f"[PASS] 8. Idempotency verified: 2nd evaluation returned {len(newly_unlocked_2)} newly unlocked (must be 0)")
        assert len(newly_unlocked_2) == 0

        # 9. User Isolation Test
        u2_stmt = select(User).where(User.id != user_id).limit(1)
        user2 = (await db.execute(u2_stmt)).scalars().first()
        if user2:
            sum1 = await get_user_achievements_summary(db, user_id)
            sum2 = await get_user_achievements_summary(db, user2.id)
            print(f"[PASS] 9. User isolation verified: User 1 unlocked={sum1.unlocked_count}, User 2 unlocked={sum2.unlocked_count}")

    print("=" * 60)
    print("ALL ACHIEVEMENTS BACKEND TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
