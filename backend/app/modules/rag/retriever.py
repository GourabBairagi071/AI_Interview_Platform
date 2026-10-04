import logging
import re
from typing import Any
import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.embedding import embedding_service
from app.modules.rag.model import InterviewQuestionVector
from app.modules.rag.schema import RetrievedQuestion

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Removes non-alphanumeric chars and lowercases for duplicate string comparison."""
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


class SemanticRetriever:
    """
    Hybrid semantic & metadata retrieval engine for interview questions.
    """

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        role: str | None = None,
        difficulty: str | None = None,
        topic: str | None = None,
        skills: list[str] | None = None,
        question_type: str | None = None,
        company: str | None = None,
        limit: int = 5,
        exclude_questions: list[str] | None = None,
        min_similarity: float = 0.15,
    ) -> list[RetrievedQuestion]:
        try:
            if not query or not query.strip():
                return []

            # 1. Generate query embedding
            query_vec = np.array(embedding_service.embed_text(query), dtype=np.float32)
            query_norm = np.linalg.norm(query_vec)
            if query_norm > 0:
                query_vec = query_vec / query_norm

            # 2. Build candidate filtering query
            # We select a candidate pool that matches metadata where possible
            stmt = select(InterviewQuestionVector)

            filters = []
            if difficulty and difficulty.lower() in ("easy", "medium", "hard"):
                # Case-insensitive match on difficulty
                filters.append(InterviewQuestionVector.difficulty.ilike(difficulty))

            if role and role.strip():
                # Allow partial role match
                filters.append(InterviewQuestionVector.role.ilike(f"%{role.strip()}%"))

            if topic and topic.strip():
                filters.append(InterviewQuestionVector.topic.ilike(f"%{topic.strip()}%"))

            if question_type and question_type.strip():
                filters.append(InterviewQuestionVector.question_type.ilike(f"%{question_type.strip()}%"))

            if company and company.strip():
                filters.append(InterviewQuestionVector.company.ilike(f"%{company.strip()}%"))

            # Execute filtered candidate query
            if filters:
                candidate_stmt = stmt.where(or_(*filters))
            else:
                candidate_stmt = stmt

            res = await db.execute(candidate_stmt)
            candidates = list(res.scalars().all())

            # If filtered candidates are too few, expand to broader pool
            if len(candidates) < limit:
                broader_res = await db.execute(stmt)
                candidates = list(broader_res.scalars().all())

            if not candidates:
                logger.info("SemanticRetriever: No question vectors found in database.")
                return []

            # 3. Prepare exclude sets
            excluded_ids = set()
            normalized_excluded_texts = set()
            excluded_vectors = []

            if exclude_questions:
                for eq in exclude_questions:
                    if not eq:
                        continue
                    clean_eq = eq.strip()
                    excluded_ids.add(clean_eq)
                    normalized_excluded_texts.add(_normalize_text(clean_eq))
                    # Also embed excluded questions for semantic deduplication (up to 10)
                    if len(excluded_vectors) < 10:
                        ev = np.array(embedding_service.embed_text(clean_eq), dtype=np.float32)
                        ev_norm = np.linalg.norm(ev)
                        if ev_norm > 0:
                            excluded_vectors.append(ev / ev_norm)

            # 4. Extract embeddings matrix
            matrix = np.array([c.embedding for c in candidates], dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1e-9
            matrix_normalized = matrix / norms

            # 5. Compute cosine similarities
            similarities = np.dot(matrix_normalized, query_vec)

            # 6. Rank and score with metadata boosts & deduplication
            scored_questions: list[tuple[float, RetrievedQuestion]] = []

            for idx, (c, sim) in enumerate(zip(candidates, similarities)):
                # Deduplication check 1: ID match
                if c.question_id in excluded_ids:
                    continue

                # Deduplication check 2: Exact normalized text match
                norm_q = _normalize_text(c.question_text)
                if norm_q in normalized_excluded_texts:
                    continue

                # Deduplication check 3: Semantic near-duplicate (> 0.88 similarity to any asked question)
                if excluded_vectors:
                    c_vec = matrix_normalized[idx]
                    near_dup = False
                    for ev in excluded_vectors:
                        if np.dot(c_vec, ev) > 0.88:
                            near_dup = True
                            break
                    if near_dup:
                        continue

                # Calculate metadata matches
                diff_match = bool(difficulty and c.difficulty and c.difficulty.lower() == difficulty.lower())
                role_match = bool(role and c.role and role.lower() in c.role.lower())
                
                # Check skill match
                skill_match = False
                c_skills = c.skills or []
                if skills:
                    target_skills_lower = {s.lower() for s in skills}
                    for cs in c_skills:
                        if cs and cs.lower() in target_skills_lower:
                            skill_match = True
                            break

                # Composite score
                raw_sim = float(sim)
                composite_score = raw_sim * 0.60
                if diff_match:
                    composite_score += 0.15
                if role_match:
                    composite_score += 0.15
                if skill_match:
                    composite_score += 0.10

                retrieved = RetrievedQuestion(
                    question_id=c.question_id,
                    question_text=c.question_text,
                    question_type=c.question_type or "Technical",
                    role=c.role,
                    difficulty=c.difficulty,
                    topic=c.topic,
                    skills=[str(s) for s in c_skills] if isinstance(c_skills, list) else [],
                    company=c.company,
                    source=c.source or "practice_bank",
                    similarity=round(raw_sim, 4),
                    relevance_score=round(composite_score, 4),
                    role_match=role_match,
                    skill_match=skill_match,
                    difficulty_match=diff_match,
                )

                scored_questions.append((composite_score, retrieved))

            # 7. Sort by composite score descending
            scored_questions.sort(key=lambda x: x[0], reverse=True)

            # Return top-K
            return [sq[1] for sq in scored_questions[:limit]]

        except Exception as e:
            logger.error(f"SemanticRetriever error during retrieval: {e}", exc_info=True)
            return []


# Global singleton instance
semantic_retriever = SemanticRetriever()
