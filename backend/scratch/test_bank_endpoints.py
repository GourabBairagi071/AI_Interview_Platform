import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.modules.auth.model import User
from app.modules.practice.service import (
    load_all_platform_questions,
    get_technologies_summary,
    get_topics_summary,
    get_practice_questions_list,
    get_user_practice_stats,
)

async def test_bank_backend():
    print("TESTING BACKEND BANK SERVICE & ENDPOINTS...")
    async with AsyncSessionLocal() as session:
        # Get test user
        r = await session.execute(select(User).order_by(User.created_at.asc()).limit(1))
        user = r.scalar_one()
        print(f"User: {user.email} ({user.id})")

        # 1. Catalog
        catalog = await load_all_platform_questions(session)
        print(f"1. Catalog loaded: {len(catalog)} questions")
        assert len(catalog) >= 5000, f"Expected >= 5000, got {len(catalog)}"

        # 2. Technologies summary
        techs_res = await get_technologies_summary(session, user.id)
        print(f"2. Technologies: {techs_res.total_technologies} total techs, {techs_res.total_questions} questions, {techs_res.total_solved} solved.")
        assert techs_res.total_technologies >= 47
        sample_tech = techs_res.technologies[0]
        print(f"   Top Tech: {sample_tech.technology} (Slug: {sample_tech.slug}), Total: {sample_tech.total_questions}, Solved: {sample_tech.solved}, Mastery: {sample_tech.mastery_percentage}%, XP: {sample_tech.xp_earned}")

        # 3. Topics summary for Python
        topics_res = await get_topics_summary(session, user.id, "python")
        print(f"3. Python Topics: {topics_res.total_topics} topics, {topics_res.total_questions} questions.")
        assert topics_res.total_topics >= 10
        sample_topic = topics_res.topics[0]
        print(f"   Sample Topic: {sample_topic.topic} (Slug: {sample_topic.slug}), Total: {sample_topic.total_questions}, Solved: {sample_topic.solved}, Remaining: {sample_topic.remaining}, Mastery: {sample_topic.mastery_percentage}%")

        # 4. Questions list for Python -> OOP with pagination
        q_list_res = await get_practice_questions_list(
            session,
            user.id,
            technology="python",
            topic="oop",
            page=1,
            page_size=5,
        )
        print(f"4. Questions List (Python -> OOP): Total {q_list_res.total} matching, Page {q_list_res.page}, Items returned: {len(q_list_res.questions)}")
        assert q_list_res.total > 0
        sample_q = q_list_res.questions[0]
        print(f"   Sample Question: '{sample_q.question[:60]}...' | Diff: {sample_q.difficulty} | Type: {sample_q.question_type} | Solved: {sample_q.solved} | XP Reward: {sample_q.xp_reward}")

        # 5. Practice stats
        stats = await get_user_practice_stats(session, user.id)
        print(f"5. Practice Stats: Level {stats.xp.level} ({stats.xp.level_title}), Total XP: {stats.xp.total_xp}, Streak: {stats.streak.current_streak} days, Overall Mastery: {stats.mastery.overall_percentage}%")
        assert stats.xp.total_xp >= 0

        print("\nALL BACKEND BANK VERIFICATIONS PASSED (100%)!")

if __name__ == "__main__":
    asyncio.run(test_bank_backend())
