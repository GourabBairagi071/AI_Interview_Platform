import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.ai_service import (
    evaluate_interview_answers,
    generate_followup_question,
    generate_interview_questions,
)
from app.modules.interview.model import Interview


# ============================================================
# CREATE INTERVIEW
# ============================================================

async def create_interview(
    db: AsyncSession,
    user_id,
    job_role: str,
    difficulty: str,
) -> Interview:

    questions = await generate_interview_questions(
        job_role=job_role,
        difficulty=difficulty,
        number_of_questions=5,
    )

    interview = Interview(
        user_id=user_id,
        job_role=job_role,
        difficulty=difficulty,
        status="created",
        questions=json.dumps(
            questions,
            ensure_ascii=False,
        ),
    )

    db.add(interview)

    await db.commit()
    await db.refresh(interview)

    return interview


# ============================================================
# GET USER INTERVIEWS
# ============================================================

async def get_user_interviews(
    db: AsyncSession,
    user_id,
) -> list[Interview]:

    result = await db.execute(
        select(Interview)
        .where(
            Interview.user_id == user_id
        )
        .order_by(
            Interview.created_at.desc()
        )
    )

    return list(
        result.scalars().all()
    )


# ============================================================
# GET SINGLE INTERVIEW
# ============================================================

async def get_user_interview(
    db: AsyncSession,
    user_id,
    interview_id,
) -> Interview | None:

    result = await db.execute(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
        )
    )

    return result.scalar_one_or_none()


# ============================================================
# START INTERVIEW
# ============================================================

async def start_interview(
    db: AsyncSession,
    interview: Interview,
) -> Interview:

    interview.status = "started"

    interview.started_at = (
        datetime.now(timezone.utc)
    )

    # Initialize transcript with questions
    try:
        questions = json.loads(
            interview.questions or "[]"
        )
    except json.JSONDecodeError:
        questions = []

    transcript = []

    for index, question in enumerate(
        questions,
        start=1,
    ):

        if not isinstance(
            question,
            dict,
        ):
            continue

        transcript.append(
            {
                "type": "question",
                "question_number": index,
                "text": question.get(
                    "question",
                    "",
                ),
                "topic": question.get(
                    "topic",
                    "",
                ),
                "difficulty": question.get(
                    "difficulty",
                    interview.difficulty,
                ),
            }
        )

    interview.transcript = json.dumps(
        transcript,
        ensure_ascii=False,
    )

    await db.commit()
    await db.refresh(interview)

    return interview


# ============================================================
# SAVE INTERVIEW ANSWERS
# ============================================================

async def save_interview_answers(
    db: AsyncSession,
    interview: Interview,
    answers: str,
) -> Interview:

    interview.answers = answers

    # --------------------------------------------------------
    # Load existing transcript
    # --------------------------------------------------------

    try:
        transcript = json.loads(
            interview.transcript or "[]"
        )
    except json.JSONDecodeError:
        transcript = []

    # --------------------------------------------------------
    # Try to parse structured answers
    # --------------------------------------------------------

    parsed_answers = None

    try:
        parsed_answers = json.loads(
            answers
        )
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        parsed_answers = None

    # --------------------------------------------------------
    # STRUCTURED ANSWERS
    # --------------------------------------------------------

    if isinstance(
        parsed_answers,
        list,
    ):

        # Remove previously stored answer entries
        # to prevent duplicate transcript entries.
        transcript = [
            item
            for item in transcript
            if item.get("type")
            not in {
                "answer",
                "followup",
                "followup_answer",
            }
        ]

        for item in parsed_answers:

            if not isinstance(
                item,
                dict,
            ):
                continue

            item_type = item.get(
                "type",
                "answer",
            )

            if item_type not in {
                "answer",
                "followup",
                "followup_answer",
            }:
                item_type = "answer"

            transcript.append(
                {
                    "type": item_type,
                    "question_number": item.get(
                        "question_number"
                    ),
                    "text": item.get(
                        "text",
                        item.get(
                            "answer",
                            "",
                        ),
                    ),
                    "difficulty": item.get(
                        "difficulty"
                    ),
                }
            )

    # --------------------------------------------------------
    # PLAIN TEXT ANSWER
    # --------------------------------------------------------

    else:

        answer_entries = [
            item
            for item in transcript
            if item.get("type")
            in {
                "answer",
                "followup_answer",
            }
        ]

        if answer_entries:

            # Update latest answer
            answer_entries[-1][
                "text"
            ] = answers

        else:

            question_numbers = [
                item.get(
                    "question_number"
                )
                for item in transcript
                if isinstance(
                    item.get(
                        "question_number"
                    ),
                    int,
                )
            ]

            next_question_number = (
                max(question_numbers)
                if question_numbers
                else 1
            )

            transcript.append(
                {
                    "type": "answer",
                    "question_number": (
                        next_question_number
                    ),
                    "text": answers,
                }
            )

    interview.transcript = json.dumps(
        transcript,
        ensure_ascii=False,
    )

    await db.commit()
    await db.refresh(interview)

    return interview


# ============================================================
# COMPLETE INTERVIEW
# ============================================================

async def complete_interview(
    db: AsyncSession,
    interview: Interview,
) -> Interview:

    if not interview.answers:
        raise ValueError(
            "Interview answers are required"
        )

    # --------------------------------------------------------
    # Parse questions
    # --------------------------------------------------------

    try:
        questions = json.loads(
            interview.questions or "[]"
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid interview questions data"
        ) from exc

    # --------------------------------------------------------
    # Evaluate interview
    # --------------------------------------------------------

    evaluation = (
        await evaluate_interview_answers(
            job_role=interview.job_role,
            questions=questions,
            answers=interview.answers,
        )
    )

    # --------------------------------------------------------
    # Overall score
    # --------------------------------------------------------

    interview.score = float(
        evaluation.get(
            "score",
            0,
        )
    )

    # --------------------------------------------------------
    # Overall feedback
    # --------------------------------------------------------

    interview.feedback = (
        evaluation.get(
            "feedback",
            "",
        )
    )

    # --------------------------------------------------------
    # Overall strengths
    # --------------------------------------------------------

    interview.strengths = json.dumps(
        evaluation.get(
            "strengths",
            [],
        ),
        ensure_ascii=False,
    )

    # --------------------------------------------------------
    # Overall weaknesses
    # --------------------------------------------------------

    interview.weaknesses = json.dumps(
        evaluation.get(
            "weaknesses",
            [],
        ),
        ensure_ascii=False,
    )

    # --------------------------------------------------------
    # Question-level evaluation
    # --------------------------------------------------------

    if hasattr(
        interview,
        "question_evaluations",
    ):

        interview.question_evaluations = (
            json.dumps(
                evaluation.get(
                    "question_evaluations",
                    [],
                ),
                ensure_ascii=False,
            )
        )

    # --------------------------------------------------------
    # Complete interview
    # --------------------------------------------------------

    interview.status = "completed"

    interview.completed_at = (
        datetime.now(timezone.utc)
    )

    await db.commit()
    await db.refresh(interview)

    return interview


# ============================================================
# GENERATE FOLLOW-UP QUESTION
# ============================================================

async def get_followup_question(
    job_role: str,
    question: str,
    answer: str,
    conversation_history: list[dict] | None = None,
) -> dict:

    return await generate_followup_question(
        job_role=job_role,
        question=question,
        answer=answer,
        conversation_history=conversation_history,
    )