import logging
import uuid
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.practice.model import PracticeQuestion
from app.modules.rag.embedding import embedding_service
from app.modules.rag.model import InterviewQuestionVector

logger = logging.getLogger(__name__)


async def index_questions_from_bank(
    db: AsyncSession,
    batch_size: int = 100,
    limit: int | None = None,
    force_reindex: bool = False,
) -> dict[str, int]:
    """
    Reads interview questions from practice_questions, creates rich embedding representations,
    and indexes them into interview_question_vectors in batches.
    Avoids duplicating already indexed questions unless force_reindex is True.
    """
    # 1. Check existing indexed question IDs
    existing_ids: set[str] = set()
    if not force_reindex:
        res = await db.execute(select(InterviewQuestionVector.question_id))
        existing_ids = set(res.scalars().all())

    # 2. Query questions to index
    stmt = select(PracticeQuestion).order_by(PracticeQuestion.created_at.asc())
    if limit is not None:
        stmt = stmt.limit(limit)

    query_res = await db.execute(stmt)
    all_questions = query_res.scalars().all()

    indexed_count = 0
    skipped_count = 0

    to_process: list[PracticeQuestion] = []
    for q in all_questions:
        if not force_reindex and q.id in existing_ids:
            skipped_count += 1
            continue
        to_process.append(q)

    total_to_index = len(to_process)
    logger.info(f"RAG Indexer: Found {len(all_questions)} practice questions. To index: {total_to_index}, Skipped: {skipped_count}")

    # Process in batches
    for i in range(0, total_to_index, batch_size):
        chunk = to_process[i : i + batch_size]

        # Prepare contextual text representations for rich semantic retrieval
        # Includes role, technology, topic, subtopic and question text
        contextual_texts = []
        for q in chunk:
            skills_str = f"{q.technology} {q.topic} {q.subtopic}".strip()
            role_str = q.role or "Software Engineer"
            text_rep = f"Role: {role_str} | Technology: {skills_str} | Difficulty: {q.difficulty} | Question: {q.question}"
            contextual_texts.append(text_rep)

        # Generate embeddings in batch
        embeddings = embedding_service.embed_batch(contextual_texts)

        for q, emb in zip(chunk, embeddings):
            skills = [s for s in [q.technology, q.topic, q.subtopic] if s and s != "General"]

            insert_stmt = pg_insert(InterviewQuestionVector).values(
                id=uuid.uuid4(),
                question_id=q.id,
                question_text=q.question,
                question_type=q.question_type or "Technical",
                role=q.role,
                difficulty=q.difficulty,
                skills=skills,
                topic=q.topic,
                company=None,
                source=q.source or "practice_bank",
                embedding=emb,
            )

            # On conflict update embedding and metadata
            do_update_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[InterviewQuestionVector.question_id],
                set_={
                    "question_text": insert_stmt.excluded.question_text,
                    "question_type": insert_stmt.excluded.question_type,
                    "role": insert_stmt.excluded.role,
                    "difficulty": insert_stmt.excluded.difficulty,
                    "skills": insert_stmt.excluded.skills,
                    "topic": insert_stmt.excluded.topic,
                    "embedding": insert_stmt.excluded.embedding,
                    "updated_at": func.now(),
                },
            )

            await db.execute(do_update_stmt)
            indexed_count += 1

        await db.commit()
        logger.info(f"Indexed batch {i // batch_size + 1}: {len(chunk)} questions (Total indexed so far: {indexed_count})")

    # Get total vector count
    total_vectors_res = await db.execute(select(func.count(InterviewQuestionVector.id)))
    total_vectors = total_vectors_res.scalar_one()

    return {
        "indexed_count": indexed_count,
        "skipped_count": skipped_count,
        "total_vectors": total_vectors,
    }


async def get_indexing_status(db: AsyncSession) -> dict[str, Any]:
    """
    Returns current indexing status and vector counts.
    """
    total_vectors_res = await db.execute(select(func.count(InterviewQuestionVector.id)))
    total_vectors = total_vectors_res.scalar_one()

    # Check if vector extension is enabled
    has_vector_ext = False
    try:
        from sqlalchemy import text
        ext_res = await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        has_vector_ext = bool(ext_res.scalar())
    except Exception:
        has_vector_ext = False

    return {
        "status": "ready" if total_vectors > 0 else "needs_indexing",
        "provider": embedding_service.provider,
        "model_name": embedding_service.model_name,
        "embedding_dimension": embedding_service.dimension,
        "total_indexed": total_vectors,
        "pgvector_available": has_vector_ext,
    }
