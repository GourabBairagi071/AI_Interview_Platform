import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.ai_service import (
    evaluate_interview_answers,
    generate_followup_question,
    generate_interview_questions,
)
from app.modules.interview.model import Interview

logger = logging.getLogger(__name__)


# ============================================================
# CREATE INTERVIEW
# ============================================================

async def create_interview(
    db: AsyncSession,
    user_id,
    job_role: str,
    difficulty: str,
    experience_level: str = "Mid-Level",
    interview_type: str = "Technical",
    number_of_questions: int = 5,
) -> Interview:

    # Build RAG grounding context from the vector database
    rag_grounding = ""
    try:
        from app.modules.rag.context_builder import build_interview_rag_context

        rag_grounding, _ = await build_interview_rag_context(
            db=db,
            job_role=job_role,
            difficulty=difficulty,
            experience_level=experience_level,
            interview_type=interview_type,
            limit=max(6, number_of_questions * 2),
        )
    except Exception as exc:
        logger.warning(f"RAG context builder fallback in create_interview: {exc}")
        rag_grounding = ""

    questions = await generate_interview_questions(
        job_role=job_role,
        difficulty=difficulty,
        experience_level=experience_level,
        interview_type=interview_type,
        number_of_questions=number_of_questions,
        rag_grounding_context=rag_grounding,
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

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        await publish_event(
            WebSocketEventType.INTERVIEW_STARTED.value,
            {
                "interview_id": str(interview.id),
                "job_role": interview.job_role,
                "status": interview.status,
            },
            user_id=interview.user_id,
        )
    except Exception as ws_err:
        logger.warning("Failed to publish interview.started event: %s", ws_err)

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

    # Update transcript entries with question-level evaluations
    try:
        cur_transcript = get_structured_transcript(interview)
        q_evals = evaluation.get("question_evaluations", [])
        eval_map = {ev.get("question_number"): ev for ev in q_evals if isinstance(ev, dict)}
        for entry in cur_transcript:
            q_num = entry.get("question_index")
            if q_num in eval_map:
                entry["evaluation"] = eval_map[q_num]
        interview.transcript = json.dumps(cur_transcript, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to merge evaluation into transcript: {e}")

    # --------------------------------------------------------
    # Complete interview
    # --------------------------------------------------------

    interview.status = "completed"

    interview.completed_at = (
        datetime.now(timezone.utc)
    )

    # Persist interview completed notification
    try:
        from app.modules.notifications.service import NotificationService
        from app.modules.notifications.schema import NotificationType
        await NotificationService.create_notification(
            db=db,
            user_id=interview.user_id,
            type=NotificationType.INTERVIEW_COMPLETED.value,
            title="Interview Completed",
            message=f"Your mock interview for '{interview.job_role or 'Software Engineer'}' is completed.",
            icon="💼",
            event_key=f"interview_completed:{interview.user_id}:{interview.id}",
            metadata={
                "interview_id": str(interview.id),
                "job_role": interview.job_role,
            },
            action_url=f"/interview/{interview.id}/results",
            priority="normal",
            commit=False,
        )
    except Exception as e:
        logger.warning(f"Failed to create interview notification: {e}")

    await db.commit()
    await db.refresh(interview)

    try:
        from app.core.websocket import publish_event, WebSocketEventType
        await publish_event(
            WebSocketEventType.INTERVIEW_COMPLETED.value,
            {
                "interview_id": str(interview.id),
                "job_role": interview.job_role,
                "score": interview.score,
                "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
            },
            user_id=interview.user_id,
        )
    except Exception as ws_err:
        logger.warning("Failed to publish interview.completed event: %s", ws_err)

    # Sync personalized learning skill performance
    try:
        from app.modules.learning.evaluator import sync_and_persist_skill_performances
        await sync_and_persist_skill_performances(db, interview.user_id)
    except Exception as e:
        logger.warning(f"Failed to auto-update skill performance on interview completion: {e}")

    return interview


# ============================================================
# GENERATE FOLLOW-UP QUESTION
# ============================================================

async def get_followup_question(
    job_role: str,
    question: str,
    answer: str,
    conversation_history: list[dict] | None = None,
    db: AsyncSession | None = None,
) -> dict:

    rag_grounding = ""
    if db is not None:
        try:
            from app.modules.rag.context_builder import build_followup_rag_context

            prev_q = []
            if conversation_history:
                for turn in conversation_history:
                    if isinstance(turn, dict) and turn.get("question"):
                        prev_q.append(turn["question"])

            rag_grounding, _ = await build_followup_rag_context(
                db=db,
                job_role=job_role,
                current_question=question,
                candidate_answer=answer,
                previous_questions=prev_q,
                limit=4,
            )
        except Exception as exc:
            logger.warning(f"RAG followup grounding fallback in get_followup_question: {exc}")
            rag_grounding = ""

    return await generate_followup_question(
        job_role=job_role,
        question=question,
        answer=answer,
        conversation_history=conversation_history,
        rag_grounding_context=rag_grounding,
    )


# ============================================================
# STRUCTURED TRANSCRIPT OPERATIONS
# ============================================================

def get_structured_transcript(interview: Interview) -> list[dict]:
    """
    Parses and normalizes the interview transcript into standardized conversation entries.
    Each entry contains:
      - question: str
      - candidate_answer: str
      - timestamp: str (ISO)
      - question_index: int
      - question_type: str ("technical" | "behavioral" | "followup")
      - is_followup: bool
      - evaluation: dict | None
    """
    try:
        raw_items = json.loads(interview.transcript or "[]")
    except Exception:
        raw_items = []

    try:
        raw_questions = json.loads(interview.questions or "[]")
    except Exception:
        raw_questions = []

    try:
        evaluations = json.loads(interview.question_evaluations or "[]")
    except Exception:
        evaluations = []

    eval_by_q_num = {}
    if isinstance(evaluations, list):
        for ev in evaluations:
            if isinstance(ev, dict) and "question_number" in ev:
                eval_by_q_num[ev["question_number"]] = ev

    # Check if raw_items already follows the new structured format
    is_new_format = False
    if isinstance(raw_items, list) and len(raw_items) > 0:
        sample = raw_items[0]
        if isinstance(sample, dict) and "question" in sample and ("candidate_answer" in sample or "question_index" in sample):
            is_new_format = True

    if is_new_format:
        result = []
        for item in raw_items:
            q_idx = item.get("question_index", 1)
            entry = dict(item)
            if not entry.get("evaluation") and q_idx in eval_by_q_num:
                entry["evaluation"] = eval_by_q_num[q_idx]
            result.append(entry)
        return result

    # Convert legacy format into standardized conversation entries
    entries: list[dict] = []
    q_map: dict[int, dict] = {}

    for idx, q in enumerate(raw_questions, start=1):
        if isinstance(q, dict):
            q_text = q.get("question", "")
            q_topic = q.get("topic", "technical")
        else:
            q_text = str(q)
            q_topic = "technical"

        q_map[idx] = {
            "question": q_text,
            "candidate_answer": "",
            "timestamp": interview.started_at.isoformat() if interview.started_at else None,
            "question_index": idx,
            "question_type": q_topic,
            "is_followup": False,
            "evaluation": eval_by_q_num.get(idx),
        }

    # Extract answers from answers text
    if interview.answers:
        blocks = interview.answers.split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n", 1)
            if lines and "Question" in lines[0]:
                prefix = lines[0]
                ans_text = lines[1].strip() if len(lines) > 1 else ""
                m = re.search(r"Question\s+(\d+)", prefix)
                if m:
                    q_num = int(m.group(1))
                    is_f = "(Follow-up)" in prefix
                    if q_num in q_map:
                        q_map[q_num]["candidate_answer"] = ans_text
                        q_map[q_num]["is_followup"] = is_f
                    else:
                        q_map[q_num] = {
                            "question": f"Question {q_num}",
                            "candidate_answer": ans_text,
                            "timestamp": None,
                            "question_index": q_num,
                            "question_type": "followup" if is_f else "technical",
                            "is_followup": is_f,
                            "evaluation": eval_by_q_num.get(q_num),
                        }

    for idx in sorted(q_map.keys()):
        entries.append(q_map[idx])

    return entries


async def save_structured_transcript(
    db: AsyncSession,
    interview: Interview,
    entries: list[dict],
) -> Interview:
    """
    Saves structured conversation transcript entries and synchronizes answers.
    """
    interview.transcript = json.dumps(entries, ensure_ascii=False)

    formatted_answers = []
    for item in entries:
        prefix = f"Question {item.get('question_index', 1)}"
        if item.get("is_followup"):
            prefix += " (Follow-up)"
        ans = item.get("candidate_answer", "").strip() or "No answer provided"
        formatted_answers.append(f"{prefix}:\n{ans}")

    if formatted_answers:
        interview.answers = "\n\n".join(formatted_answers)

    await db.commit()
    await db.refresh(interview)
    return interview