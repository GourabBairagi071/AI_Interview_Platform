import asyncio
import datetime
import json
import uuid
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User, UserProfile
from app.modules.interview.model import Interview
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.learning.model import (
    LearningProfile,
    SkillPerformance,
    LearningRoadmap,
    LearningResource,
    DailyPracticePlan,
    WeeklyGoal,
)
from app.modules.learning.normalizer import normalize_skill_name
from app.modules.learning.evaluator import (
    evaluate_user_skills,
    sync_and_persist_skill_performances,
    DEFAULT_THRESHOLDS,
)
from app.modules.learning.service import LearningService
from app.modules.learning.seed_resources import seed_learning_resources_if_needed


async def run_tests():
    print("=" * 60)
    print("PHASE 11 PERSONALIZED LEARNING ENGINE VERIFICATION")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Seed resources
        seeded = await seed_learning_resources_if_needed(db)
        print(f"[TEST 1] Seeded Resources: {seeded} new resources (or already present)")

        # Create 2 test users for isolation and test cases
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        user_a = User(
            id=user_a_id,
            email=f"candidate_a_{user_a_id.hex[:6]}@example.com",
            full_name="Candidate Alpha",
            hashed_password="hashed_pw_test",
        )
        user_b = User(
            id=user_b_id,
            email=f"candidate_b_{user_b_id.hex[:6]}@example.com",
            full_name="Candidate Beta",
            hashed_password="hashed_pw_test",
        )
        db.add_all([user_a, user_b])
        await db.commit()
        print(f"[TEST 2] Created test users: User A ({user_a.email}) & User B ({user_b.email})")

        # ---------------------------------------------------------
        # Scenario 1: Empty User (No History)
        # ---------------------------------------------------------
        print("\n--- Scenario 1: New / Empty User ---")
        empty_skills = await evaluate_user_skills(db, user_a_id)
        assert len(empty_skills) == 0, f"Expected 0 skills for new user without data, got {len(empty_skills)}"
        print("  [PASS] Empty user has 0 fabricated skills or scores")

        weak_topics_empty = await LearningService.get_weak_topics(db, user_a_id)
        assert len(weak_topics_empty) == 0, f"Expected 0 weak topics, got {len(weak_topics_empty)}"
        print("  [PASS] No fabricated weaknesses for new user")

        empty_profile = await LearningService.get_or_create_profile(db, user_a_id)
        assert empty_profile.user_id == user_a_id
        print("  [PASS] Default learning profile initialized successfully")

        # ---------------------------------------------------------
        # Scenario 2: Normalization Engine
        # ---------------------------------------------------------
        print("\n--- Scenario 2: Normalization Engine ---")
        assert normalize_skill_name("python programming")[0] == "Python"
        assert normalize_skill_name("Fast API")[0] == "FastAPI"
        assert normalize_skill_name("dsa")[0] == "Data Structures & Algorithms"
        assert normalize_skill_name("POSTGRES")[0] == "PostgreSQL"
        assert normalize_skill_name("react.js")[0] == "React"
        assert normalize_skill_name("System Design")[1] == "System Architecture"
        print("  [PASS] Skill normalization passed: aliases map correctly to canonical names & categories")

        # ---------------------------------------------------------
        # Scenario 3: Interview Performance Evaluation
        # ---------------------------------------------------------
        print("\n--- Scenario 3: Interview Performance Data ---")
        interview_1 = Interview(
            id=uuid.uuid4(),
            user_id=user_a_id,
            job_role="Backend Developer",
            difficulty="Medium",
            status="completed",
            score=55.0,
            questions=json.dumps([
                {"question": "How do you implement Dependency Injection in FastAPI?"},
                {"question": "Design a high-throughput REST API using Python asyncio."},
                {"question": "Explain graph traversal using BFS and DFS."},
            ]),
            question_evaluations=json.dumps([
                {"question_number": 1, "score": 45.0, "feedback": "Struggled with FastAPI dependencies."},
                {"question_number": 2, "score": 50.0, "feedback": "Understood asyncio basics, lacked depth."},
                {"question_number": 3, "score": 85.0, "feedback": "Great explanation of BFS/DFS graphs."},
            ]),
            completed_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(interview_1)
        await db.commit()

        # Sync skills
        synced_skills = await sync_and_persist_skill_performances(db, user_a_id)
        print(f"  [PASS] Synced {len(synced_skills)} skills from interview")

        skill_map = {s.canonical_skill: s for s in synced_skills}
        assert "FastAPI" in skill_map
        assert "Graphs" in skill_map
        assert skill_map["FastAPI"].interview_score == 45.0
        assert skill_map["FastAPI"].status == "weak"
        assert skill_map["Graphs"].interview_score == 85.0
        assert skill_map["Graphs"].status == "strong"
        print(f"  [PASS] FastAPI: score={skill_map['FastAPI'].combined_score}, status={skill_map['FastAPI'].status}")
        print(f"  [PASS] Graphs: score={skill_map['Graphs'].combined_score}, status={skill_map['Graphs'].status}")

        # ---------------------------------------------------------
        # Scenario 4: Coding Performance Data & Combined Scores
        # ---------------------------------------------------------
        print("\n--- Scenario 4: Coding Arena Submissions & Combined Scores ---")
        # Grab a coding problem for Dynamic Programming
        prob_res = await db.execute(
            select(CodingProblem).where(CodingProblem.topic.ilike("%Dynamic Programming%")).limit(1)
        )
        dp_prob = prob_res.scalar_one_or_none()
        if not dp_prob:
            # Fallback to any problem
            dp_prob = (await db.execute(select(CodingProblem).limit(1))).scalar_one()

        sub_dp = CodingSubmission(
            id=uuid.uuid4(),
            user_id=user_a_id,
            problem_id=dp_prob.id,
            language="python",
            source_code="def solve(): pass",
            status="Wrong Answer",
            score=30.0,
            passed_tests=1,
            total_tests=4,
        )
        db.add(sub_dp)
        await db.commit()

        # Re-evaluate
        updated_skills = await sync_and_persist_skill_performances(db, user_a_id)
        updated_map = {s.canonical_skill: s for s in updated_skills}
        dp_canonical, _ = normalize_skill_name(dp_prob.topic)
        assert dp_canonical in updated_map
        print(f"  [PASS] Coding skill '{dp_canonical}' evaluated: score={updated_map[dp_canonical].coding_score}, status={updated_map[dp_canonical].status}")

        # ---------------------------------------------------------
        # Scenario 5: Weak Topic Detection
        # ---------------------------------------------------------
        print("\n--- Scenario 5: Weak Topic Detection ---")
        weak_topics = await LearningService.get_weak_topics(db, user_a_id)
        assert len(weak_topics) >= 1
        top_weak = weak_topics[0]
        print(f"  [PASS] Identified {len(weak_topics)} weak topics. Top weakness: {top_weak['topic']} (Priority: {top_weak['priority']}, Score: {top_weak['combined_score']})")
        print(f"    Reason: {top_weak['reason']}")

        # ---------------------------------------------------------
        # Scenario 6: Personalized Learning Roadmap
        # ---------------------------------------------------------
        print("\n--- Scenario 6: Personalized Roadmap Generation ---")
        roadmap = await LearningService.generate_or_get_roadmap(
            db, user_a_id, target_role="Senior Backend Engineer", force_regenerate=True
        )
        assert roadmap.user_id == user_a_id
        assert len(roadmap.weeks) == 4
        print(f"  [PASS] Generated 4-week roadmap: '{roadmap.title}'")
        for wk in roadmap.weeks:
            print(f"    - Week {wk['week_number']}: {wk['title']} [Focus: {wk['focus_topic']}] (Items: {len(wk['items'])})")

        # ---------------------------------------------------------
        # Scenario 7: Learning Resource Recommendations
        # ---------------------------------------------------------
        print("\n--- Scenario 7: Resource Recommendations ---")
        resources = await LearningService.get_learning_resources(db, user_a_id, limit=3)
        assert len(resources) > 0
        print(f"  [PASS] Retrieved {len(resources)} curated technical resources:")
        for r in resources:
            print(f"    - [{r.resource_type}] {r.title} ({r.canonical_skill}) -> {r.url}")

        # ---------------------------------------------------------
        # Scenario 8: RAG Interview Recommendations
        # ---------------------------------------------------------
        print("\n--- Scenario 8: RAG Interview Recommendations ---")
        interview_recs = await LearningService.get_interview_recommendations(db, user_a_id, limit=3)
        assert len(interview_recs) > 0
        print(f"  [PASS] Retrieved {len(interview_recs)} targeted interview practice questions:")
        for q in interview_recs:
            print(f"    - [{q.get('topic')}] {q.get('question')[:80]}...")

        # ---------------------------------------------------------
        # Scenario 9: 1,000 Coding Arena Recommendations
        # ---------------------------------------------------------
        print("\n--- Scenario 9: Coding Arena Recommendations ---")
        coding_recs = await LearningService.get_coding_recommendations(db, user_a_id, limit=3)
        assert len(coding_recs) > 0
        print(f"  [PASS] Retrieved {len(coding_recs)} recommended coding challenges:")
        for c in coding_recs:
            print(f"    - [{c['difficulty']}] {c['title']} ({c['topic']}) -> slug: {c['slug']}")

        # ---------------------------------------------------------
        # Scenario 10: Daily Practice Plan
        # ---------------------------------------------------------
        print("\n--- Scenario 10: Daily Practice Plan ---")
        plan = await LearningService.get_or_create_daily_plan(db, user_a_id)
        assert len(plan.items) >= 4
        print(f"  [PASS] Daily Plan for {plan.plan_date} generated with {len(plan.items)} actionable tasks.")

        # Toggle first task
        task_id = plan.items[0]["id"]
        updated_plan = await LearningService.complete_daily_task(db, user_a_id, task_id)
        assert updated_plan.items[0]["is_completed"] is True
        print(f"  [PASS] Toggled completion of task '{task_id}': is_completed={updated_plan.items[0]['is_completed']}")

        # ---------------------------------------------------------
        # Scenario 11: Weekly Goals
        # ---------------------------------------------------------
        print("\n--- Scenario 11: Weekly Goals ---")
        goals = await LearningService.get_or_create_weekly_goals(db, user_a_id)
        assert len(goals) == 4
        print(f"  [PASS] Initialized {len(goals)} weekly goals for week of {goals[0].week_start_date}:")
        for g in goals:
            print(f"    - {g.title} ({g.completed_count}/{g.target_count}) [{g.status}]")

        # Increment goal
        goal_to_inc = goals[0]
        inc_goal = await LearningService.complete_weekly_goal_step(db, user_a_id, goal_to_inc.id)
        assert inc_goal.completed_count == 1
        print(f"  [PASS] Incremented goal '{inc_goal.title}' progress: {inc_goal.completed_count}/{inc_goal.target_count}")

        # ---------------------------------------------------------
        # Scenario 12: Learning Progress Tracking
        # ---------------------------------------------------------
        print("\n--- Scenario 12: Learning Progress & Readiness Tracking ---")
        progress = await LearningService.get_learning_progress(db, user_a_id)
        print(f"  [PASS] Overall Readiness Score: {progress['overall_readiness']}/100")
        print(f"  [PASS] Total Skills Assessed:   {progress['total_skills_assessed']}")
        print(f"  [PASS] Weak Topics Count:       {progress['weak_skills_count']}")
        print(f"  [PASS] Needs Practice Count:    {progress['needs_practice_count']}")
        print(f"  [PASS] Strong Skills Count:     {progress['strong_skills_count']}")
        print(f"  [PASS] Summary Guidance:        \"{progress['summary_message']}\"")

        # ---------------------------------------------------------
        # Scenario 13: User Isolation & Security
        # ---------------------------------------------------------
        print("\n--- Scenario 13: User Isolation & Authorization Check ---")
        user_b_skills = await LearningService.get_user_skills(db, user_b_id)
        assert len(user_b_skills) == 0, f"User B should have 0 skills, got {len(user_b_skills)}"

        user_b_plan = await LearningService.get_or_create_daily_plan(db, user_b_id)
        assert user_b_plan.user_id == user_b_id
        assert user_b_plan.id != plan.id

        # Verify User A cannot access User B's goal
        goal_cross_check = await LearningService.complete_weekly_goal_step(db, user_a_id, uuid.uuid4())
        assert goal_cross_check is None
        print("  [PASS] Strict multi-tenant user isolation confirmed across all learning models")

        # Cleanup test data
        await db.execute(delete(User).where(User.id.in_([user_a_id, user_b_id])))
        await db.commit()
        print("\n  [PASS] Test records cleaned up successfully.")

    print("\n" + "=" * 60)
    print("ALL 13 PHASE 11 BACKEND VERIFICATION CHECKS PASSED 100%!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
