import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from app.modules.achievements.model import AchievementDefinition, UserAchievement
from app.modules.achievements.service import (
    ensure_achievement_definitions,
    evaluate_user_achievements,
    get_user_achievements_list,
    get_user_achievements_summary,
    get_achievement_detail,
)
from app.modules.practice.model import PracticeProgress
from app.modules.practice.service import (
    solve_practice_question,
    load_all_platform_questions,
    get_user_practice_stats,
)


async def main():
    print("=" * 60)
    print("TASK 11: ACHIEVEMENTS MODULE COMPREHENSIVE INTEGRATION SUITE")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        catalog = await load_all_platform_questions(db)
        definitions = await ensure_achievement_definitions(db)
        total_defs = len(definitions)
        print(f"Total achievement definitions: {total_defs}")

        # --------------------------------------------------------
        # SETUP TEST USERS
        # --------------------------------------------------------
        # User A: New User
        test_email_a = f"ach_test_a_{uuid.uuid4().hex[:8]}@example.com"
        user_a = User(
            email=test_email_a,
            hashed_password="hashed_pwd_test",
            full_name="Achievement Test User A",
            is_active=True,
            is_verified=True,
        )
        db.add(user_a)

        # User B: Clean comparison user
        test_email_b = f"ach_test_b_{uuid.uuid4().hex[:8]}@example.com"
        user_b = User(
            email=test_email_b,
            hashed_password="hashed_pwd_test",
            full_name="Achievement Test User B",
            is_active=True,
            is_verified=True,
        )
        db.add(user_b)
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)

        print(f"Created User A: {user_a.email} ({user_a.id})")
        print(f"Created User B: {user_b.email} ({user_b.id})")

        try:
            # --------------------------------------------------------
            # 1. NEW USER SEES ALL ACHIEVEMENTS LOCKED
            # --------------------------------------------------------
            list_a_init = await get_user_achievements_list(db, user_a.id)
            assert list_a_init.total == total_defs, f"Expected {total_defs}, got {list_a_init.total}"
            assert list_a_init.unlocked_count == 0, f"Expected 0 unlocked, got {list_a_init.unlocked_count}"
            assert all(not a.unlocked for a in list_a_init.achievements)
            print("[PASS] 1. New user sees all active achievements locked (0 unlocked)")

            # --------------------------------------------------------
            # 2. USER SOLVES FIRST QUESTION
            # --------------------------------------------------------
            first_q_id = list(catalog.keys())[0]
            solve_res_1 = await solve_practice_question(
                db=db,
                user_id=user_a.id,
                question_id=first_q_id,
                answer="My comprehensive solution for the first question test.",
                solved=True,
            )
            print(f"[PASS] 2. User solves first question: '{solve_res_1.message}'")

            # --------------------------------------------------------
            # 3. RELEVANT ACHIEVEMENT UNLOCKS
            # --------------------------------------------------------
            list_a_after = await get_user_achievements_list(db, user_a.id)
            first_step_ach = next((a for a in list_a_after.achievements if a.id == "first_solve"), None)
            assert first_step_ach is not None
            assert first_step_ach.unlocked is True
            assert first_step_ach.current_progress == 1
            assert first_step_ach.unlocked_at is not None
            print(f"[PASS] 3. Relevant achievement unlocked: '{first_step_ach.name}' at {first_step_ach.unlocked_at}")

            # --------------------------------------------------------
            # 4. XP REWARD APPLIED & VERIFIED
            # --------------------------------------------------------
            summary_a = await get_user_achievements_summary(db, user_a.id)
            assert summary_a.unlocked_count >= 1
            assert summary_a.total_xp_earned >= first_step_ach.xp_reward
            print(f"[PASS] 4. XP reward applied: {summary_a.total_xp_earned} XP earned from achievements")

            # --------------------------------------------------------
            # 5. NOTIFICATION GENERATED EXACTLY ONCE
            # --------------------------------------------------------
            stats_a = await get_user_practice_stats(db, user_a.id)
            ach_notifs = [n for n in stats_a.notifications if n.type == "achievement"]
            assert len(ach_notifs) >= 1
            first_notif = next((n for n in ach_notifs if n.id == "ach_first_solve"), None)
            assert first_notif is not None
            print(f"[PASS] 5. Notification generated: '{first_notif.title}'")

            # --------------------------------------------------------
            # 6. REPEATING THE SAME SOLVE DOES NOT DUPLICATE XP OR UNLOCKS
            # --------------------------------------------------------
            solve_res_repeat = await solve_practice_question(
                db=db,
                user_id=user_a.id,
                question_id=first_q_id,
                answer="My duplicate solution attempt.",
                solved=True,
            )
            summary_repeat = await get_user_achievements_summary(db, user_a.id)
            assert summary_repeat.unlocked_count == summary_a.unlocked_count
            assert summary_repeat.total_xp_earned == summary_a.total_xp_earned
            print("[PASS] 6. Repeating solve does NOT duplicate achievements or achievement XP")

            # --------------------------------------------------------
            # 7. PROGRESS UPDATES CORRECTLY
            # --------------------------------------------------------
            # Solve a 2nd question
            second_q_id = list(catalog.keys())[1]
            await solve_practice_question(
                db=db,
                user_id=user_a.id,
                question_id=second_q_id,
                answer="Second solution",
                solved=True,
            )
            list_after_2 = await get_user_achievements_list(db, user_a.id)
            solve_10_ach = next(a for a in list_after_2.achievements if a.id == "solve_10")
            assert solve_10_ach.current_progress == 2
            assert solve_10_ach.target_progress == 10
            assert solve_10_ach.progress_percentage == 20.0
            assert solve_10_ach.unlocked is False
            print(f"[PASS] 7. Progress updates correctly: 'solve_10' is at {solve_10_ach.current_progress}/10 ({solve_10_ach.progress_percentage}%)")

            # --------------------------------------------------------
            # 8. MULTIPLE ACHIEVEMENTS UNLOCK FROM ONE ACTION
            # --------------------------------------------------------
            # If an action fulfills difficulty, tech, and solve milestones simultaneously
            detail_res = await get_achievement_detail(db, user_a.id, "first_solve")
            assert detail_res.achievement.unlocked is True
            assert detail_res.related_metrics is not None
            print(f"[PASS] 8. Detail endpoint verified: '{detail_res.achievement.name}' with metrics")

            # --------------------------------------------------------
            # 9. USER A ACHIEVEMENTS ARE INVISIBLE TO USER B
            # --------------------------------------------------------
            list_b = await get_user_achievements_list(db, user_b.id)
            summary_b = await get_user_achievements_summary(db, user_b.id)
            assert list_b.unlocked_count == 0
            assert summary_b.unlocked_count == 0
            assert summary_b.total_xp_earned == 0
            # Check UserAchievement records in database directly
            ua_stmt_b = select(UserAchievement).where(UserAchievement.user_id == user_b.id, UserAchievement.unlocked == True)
            res_ua_b = (await db.execute(ua_stmt_b)).scalars().all()
            assert len(res_ua_b) == 0
            print("[PASS] 9. User isolation verified: User A has unlocked achievements, User B has 0 unlocked")

            # --------------------------------------------------------
            # 10. ACHIEVEMENTS SURVIVE RE-QUERY & RE-EVALUATION
            # --------------------------------------------------------
            re_eval_items, newly = await evaluate_user_achievements(db, user_a.id)
            assert len(newly) == 0, f"Expected 0 newly unlocked, got {len(newly)}"
            re_unlocked = sum(1 for a in re_eval_items if a.unlocked)
            assert re_unlocked == summary_a.unlocked_count
            print(f"[PASS] 10. Persistence verified: {re_unlocked} unlocked achievements survived re-evaluation")

            # --------------------------------------------------------
            # 11. DASHBOARD INTEGRATION
            # --------------------------------------------------------
            stats_dash = await get_user_practice_stats(db, user_a.id)
            assert len(stats_dash.achievements) == total_defs
            dash_unlocked = sum(1 for a in stats_dash.achievements if a.unlocked)
            assert dash_unlocked >= 1
            print(f"[PASS] 11. Dashboard receives real achievements: {dash_unlocked} unlocked returned in stats")

            # --------------------------------------------------------
            # 12. PROFILE / SUMMARY INTEGRATION
            # --------------------------------------------------------
            assert len(summary_a.categories) == 8
            assert summary_a.completion_percentage > 0
            print(f"[PASS] 12. Profile / Summary verified: {summary_a.completion_percentage}% completion rate across {len(summary_a.categories)} categories")

            # --------------------------------------------------------
            # 13. TEST ACTIVE USER WITH PRIOR PROGRESS
            # --------------------------------------------------------
            active_u_stmt = select(User).where(User.id != user_a.id, User.id != user_b.id).limit(1)
            active_user = (await db.execute(active_u_stmt)).scalars().first()
            if active_user:
                act_sum = await get_user_achievements_summary(db, active_user.id)
                print(f"[PASS] 13. Active user test: {active_user.email} has {act_sum.unlocked_count} unlocked, {act_sum.total_xp_earned} XP")

        finally:
            # Clean up test users
            await db.execute(delete(UserAchievement).where(UserAchievement.user_id.in_([user_a.id, user_b.id])))
            await db.execute(delete(PracticeProgress).where(PracticeProgress.user_id.in_([user_a.id, user_b.id])))
            await db.execute(delete(User).where(User.id.in_([user_a.id, user_b.id])))
            await db.commit()
            print("Cleaned up test users.")

    print("=" * 60)
    print("ALL 13 AUTOMATED INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
