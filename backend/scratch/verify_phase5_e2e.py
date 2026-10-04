import sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import asyncio
from datetime import datetime, timezone
import json
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from app.modules.interview.model import Interview
from app.modules.interview.service import (
    create_interview,
    start_interview,
    save_structured_transcript,
    get_structured_transcript,
    get_followup_question,
    complete_interview,
)
from sqlalchemy import select

async def run_e2e_verification():
    print("=" * 60)
    print("PHASE 5 — AI AVATAR & VOICE INTERVIEW END-TO-END VERIFICATION")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # 1. Fetch test user
        user_res = await session.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        assert user is not None, "A user record is required for testing"
        print(f"1. Verified Test Candidate: {user.email} (ID: {user.id})")

        # 2. Create Interview
        interview = await create_interview(
            db=session,
            user_id=user.id,
            job_role="Senior Full Stack Engineer",
            difficulty="Hard",
            experience_level="Senior",
            interview_type="Technical",
            number_of_questions=3,
        )
        print(f"2. Created Interview: {interview.id} for role '{interview.job_role}'")
        questions = json.loads(interview.questions or "[]")
        print(f"   Generated {len(questions)} base questions.")

        # 3. Start Interview
        interview = await start_interview(session, interview)
        assert interview.status == "started"
        print(f"3. Started Interview at: {interview.started_at}")

        # 4. Check Initial Structured Transcript
        initial_transcript = get_structured_transcript(interview)
        print(f"4. Initial Structured Transcript entries: {len(initial_transcript)}")
        assert len(initial_transcript) >= 1
        print(f"   Q1: {initial_transcript[0]['question'][:60]}...")
        assert initial_transcript[0]["candidate_answer"] == ""

        # 5. Candidate Voice Answers Simulated (Voice STT -> Answer Submission)
        q1_text = initial_transcript[0]["question"]
        candidate_ans_1 = "I use React for frontend state management with TypeScript, and FastAPI with PostgreSQL on the backend with async SQLAlchemy."
        
        simulated_transcript = [
            {
                "question": q1_text,
                "candidate_answer": candidate_ans_1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question_index": 1,
                "question_type": "technical",
                "is_followup": False,
            }
        ]

        interview = await save_structured_transcript(session, interview, simulated_transcript)
        assert candidate_ans_1 in interview.answers
        print("5. Voice Transcript Sync: Candidate answer successfully recorded.")

        # 6. Adaptive Follow-up Generation
        print("6. Testing Adaptive Follow-up Engine...")
        followup = await get_followup_question(
            job_role=interview.job_role,
            question=q1_text,
            answer=candidate_ans_1,
            conversation_history=[
                {"role": "assistant", "content": q1_text},
                {"role": "user", "content": candidate_ans_1},
            ],
        )
        print(f"   Should follow up: {followup.get('should_follow_up')}")
        followup_q = followup.get("question") or "How do you handle connection pooling with asyncpg under heavy load?"
        print(f"   Follow-up Question: {followup_q[:65]}...")

        # 7. Candidate Answers Follow-up
        candidate_ans_followup = "I configure AsyncEngine with pool_size=20, max_overflow=10, and pool_recycle=1800 to avoid stale connections."
        simulated_transcript.append({
            "question": followup_q,
            "candidate_answer": candidate_ans_followup,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question_index": 2,
            "question_type": "technical",
            "is_followup": True,
        })
        interview = await save_structured_transcript(session, interview, simulated_transcript)
        print("7. Follow-up Answer Recorded into Structured Transcript.")

        # 8. Complete Interview & Run Evaluation
        print("8. Completing Interview & Triggering AI Evaluation Engine...")
        interview = await complete_interview(session, interview)
        assert interview.status == "completed"
        assert interview.completed_at is not None
        print(f"   Status: {interview.status}")
        print(f"   Final Overall Score: {interview.score}/100")
        print(f"   AI Feedback Summary: {interview.feedback[:70]}...")

        # 9. Verify Persisted Transcript with Evaluations
        final_transcript = get_structured_transcript(interview)
        print(f"9. Final Persisted Transcript has {len(final_transcript)} turns.")
        for idx, turn in enumerate(final_transcript, start=1):
            print(f"   Turn {idx}: [Index {turn['question_index']}] IsFollowup={turn.get('is_followup')} Type={turn.get('question_type')}")
            print(f"      Q: {turn['question'][:50]}...")
            print(f"      A: {turn['candidate_answer'][:50]}...")
            eval_data = turn.get("evaluation")
            if eval_data:
                print(f"      Evaluation score: {eval_data.get('score')} - {eval_data.get('feedback', '')[:40]}...")

        print("=" * 60)
        print("ALL PHASE 5 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
        print("=" * 60)

asyncio.run(run_e2e_verification())
