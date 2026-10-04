import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.retriever import semantic_retriever
from app.modules.rag.schema import RetrievedQuestion

logger = logging.getLogger(__name__)


async def build_interview_rag_context(
    db: AsyncSession,
    job_role: str,
    difficulty: str,
    experience_level: str = "Mid-Level",
    interview_type: str = "Technical",
    skills: list[str] | None = None,
    previous_questions: list[str] | None = None,
    limit: int = 6,
) -> tuple[str, list[RetrievedQuestion]]:
    """
    Builds grounding context for initial interview question generation.
    Retrieves top relevant questions from the vector bank matching the candidate's target profile.
    Returns:
      (prompt_grounding_block: str, retrieved_questions: list[RetrievedQuestion])
    """
    query_parts = [job_role, difficulty, interview_type]
    if skills:
        query_parts.extend(skills)
    query_str = " ".join(query_parts)

    try:
        retrieved = await semantic_retriever.retrieve(
            db=db,
            query=query_str,
            role=job_role,
            difficulty=difficulty,
            skills=skills,
            question_type=interview_type if interview_type != "Mixed" else None,
            limit=limit,
            exclude_questions=previous_questions,
        )

        if not retrieved:
            return "", []

        lines = [
            "============================================================",
            "GROUNDING CONTEXT: VERIFIED INDUSTRY INTERVIEW QUESTIONS",
            "Use the following questions and technical topics as foundational guidance",
            "for selecting and formulating the interview questions:",
            "============================================================",
        ]

        for i, q in enumerate(retrieved, start=1):
            skills_str = ", ".join(q.skills) if q.skills else q.topic
            lines.append(f"[{i}] Topic: {q.topic} ({skills_str}) | Level: {q.difficulty}")
            lines.append(f"    Reference Question: {q.question_text}")

        lines.append("============================================================")
        return "\n".join(lines), retrieved

    except Exception as e:
        logger.warning(f"Failed to build interview RAG context: {e}")
        return "", []


async def build_followup_rag_context(
    db: AsyncSession,
    job_role: str,
    current_question: str,
    candidate_answer: str,
    previous_questions: list[str] | None = None,
    limit: int = 4,
) -> tuple[str, list[RetrievedQuestion]]:
    """
    Builds adaptive grounding context for follow-up questions.
    Uses current question and candidate's answer keywords to retrieve deeper conceptual/practical follow-ups.
    """
    # Formulate follow-up semantic query from question and answer
    query_str = f"{current_question} {candidate_answer[:200]}"

    exclude_list = list(previous_questions or [])
    exclude_list.append(current_question)

    try:
        retrieved = await semantic_retriever.retrieve(
            db=db,
            query=query_str,
            role=job_role,
            limit=limit,
            exclude_questions=exclude_list,
        )

        if not retrieved:
            return "", []

        lines = [
            "============================================================",
            "GROUNDING CONTEXT: RELATED DEEPER QUESTIONS FROM QUESTION BANK",
            "You may ground your adaptive follow-up on these related technical concepts:",
            "============================================================",
        ]

        for i, q in enumerate(retrieved, start=1):
            lines.append(f"- Topic: {q.topic} ({q.difficulty}): {q.question_text}")

        lines.append("============================================================")
        return "\n".join(lines), retrieved

    except Exception as e:
        logger.warning(f"Failed to build follow-up RAG context: {e}")
        return "", []
