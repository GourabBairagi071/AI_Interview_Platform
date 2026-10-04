import sys
sys.path.insert(0, ".")
import asyncio
from app.core.database import AsyncSessionLocal
from app.modules.interview.model import Interview
from app.modules.interview.service import get_structured_transcript, save_structured_transcript
from sqlalchemy import select

async def test_transcript():
    async with AsyncSessionLocal() as session:
        # Fetch any existing interview
        res = await session.execute(select(Interview).limit(1))
        interview = res.scalar_one_or_none()
        if not interview:
            print("No interview found to test.")
            return

        print(f"Testing transcript for interview: {interview.id}")
        entries = get_structured_transcript(interview)
        print(f"Parsed entries count: {len(entries)}")
        if entries:
            print("First entry sample:")
            for k, v in entries[0].items():
                print(f"  {k}: {v}")

        # Test saving structured transcript
        test_entries = [
            {
                "question": "What is dependency injection?",
                "candidate_answer": "It is a design pattern where an object receives other objects that it depends on.",
                "timestamp": "2026-10-03T21:15:00Z",
                "question_index": 1,
                "question_type": "technical",
                "is_followup": False,
                "evaluation": {"score": 9.5, "feedback": "Accurate definition."},
            },
            {
                "question": "Can you explain how FastAPI handles dependency injection?",
                "candidate_answer": "FastAPI uses Depends() in path operation functions.",
                "timestamp": "2026-10-03T21:16:00Z",
                "question_index": 2,
                "question_type": "technical",
                "is_followup": True,
                "evaluation": None,
            }
        ]

        await save_structured_transcript(session, interview, test_entries)
        reloaded_entries = get_structured_transcript(interview)
        assert len(reloaded_entries) == 2, f"Expected 2, got {len(reloaded_entries)}"
        assert reloaded_entries[0]["question_index"] == 1
        assert reloaded_entries[1]["is_followup"] is True
        assert "Question 1:\nIt is a design pattern" in interview.answers
        print("Transcript get & save verified successfully 100%!")

asyncio.run(test_transcript())
