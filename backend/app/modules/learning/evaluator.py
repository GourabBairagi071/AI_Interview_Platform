from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.model import UserProfile
from app.modules.coding.model import CodingProblem, CodingSubmission
from app.modules.interview.model import Interview
from app.modules.learning.model import SkillPerformance
from app.modules.learning.normalizer import CANONICAL_SKILLS_MAP, normalize_skill_name
from app.modules.resume.model import Resume

logger = logging.getLogger(__name__)


@dataclass
class ThresholdConfig:
    weak_threshold: float = 60.0
    needs_practice_threshold: float = 80.0
    high_confidence_attempts: int = 5
    medium_confidence_attempts: int = 2


DEFAULT_THRESHOLDS = ThresholdConfig()


def _infer_skills_from_text(text: str) -> list[tuple[str, str]]:
    """Identifies skills from question text or job role using canonical map."""
    found: set[tuple[str, str]] = set()
    cleaned = re.sub(r"[^\w\s\+\#]+", " ", text.lower())
    text_lower = f" {cleaned} "
    for key, (canonical, category) in CANONICAL_SKILLS_MAP.items():
        if len(key) >= 2 and f" {key} " in text_lower:
            found.add((canonical, category))
    return list(found)


async def evaluate_user_skills(
    db: AsyncSession,
    user_id: uuid.UUID,
    thresholds: ThresholdConfig = DEFAULT_THRESHOLDS,
) -> dict[str, dict[str, Any]]:
    """
    Analyzes actual performance data for the candidate across:
    1. Resume / UserProfile skills (baseline existence)
    2. Completed Interview evaluations & question scores
    3. Coding Arena submissions & problem topics

    Returns a dictionary of canonical_skill -> skill metrics.
    DO NOT invent scores when no data exists.
    """
    skill_data: dict[str, dict[str, Any]] = {}

    def _ensure_skill(canonical: str, category: str):
        if canonical not in skill_data:
            skill_data[canonical] = {
                "canonical_skill": canonical,
                "category": category,
                "interview_scores": [],
                "coding_scores": [],
                "interview_attempts": 0,
                "coding_attempts": 0,
                "sources": [],
            }

    # -------------------------------------------------------------
    # 1. Baseline skills from UserProfile & Resume (no invented scores)
    # -------------------------------------------------------------
    profile_res = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    user_profile = profile_res.scalar_one_or_none()
    if user_profile and user_profile.skills:
        raw_skills = [s.strip() for s in user_profile.skills.split(",") if s.strip()]
        for s in raw_skills:
            can_name, category = normalize_skill_name(s)
            _ensure_skill(can_name, category)
            skill_data[can_name]["sources"].append("profile")

    resume_res = await db.execute(
        select(Resume).where(Resume.user_id == user_id)
    )
    resume = resume_res.scalar_one_or_none()
    if resume and hasattr(resume, "filename"):
        pass

    # -------------------------------------------------------------
    # 2. Extract performance from Completed Interviews
    # -------------------------------------------------------------
    interviews_res = await db.execute(
        select(Interview).where(
            Interview.user_id == user_id,
            Interview.status == "completed",
        ).order_by(Interview.completed_at.desc())
    )
    interviews = list(interviews_res.scalars().all())

    for interview in interviews:
        raw_questions = []
        try:
            if interview.questions:
                raw_questions = json.loads(interview.questions)
        except Exception:
            raw_questions = []

        q_evals = []
        try:
            if interview.question_evaluations:
                q_evals = json.loads(interview.question_evaluations)
        except Exception:
            q_evals = []

        # If question-level evaluations exist, score per question topic
        if q_evals and isinstance(q_evals, list):
            eval_map = {
                ev.get("question_number", idx + 1): ev
                for idx, ev in enumerate(q_evals)
                if isinstance(ev, dict)
            }
            for idx, q_item in enumerate(raw_questions):
                q_num = idx + 1
                q_text = q_item.get("question", "") if isinstance(q_item, dict) else str(q_item)
                matched_skills = _infer_skills_from_text(q_text)
                if not matched_skills:
                    # Fallback to role inference
                    matched_skills = _infer_skills_from_text(interview.job_role)

                ev = eval_map.get(q_num)
                if ev and "score" in ev:
                    score_val = float(ev["score"])
                    for can_name, category in matched_skills:
                        _ensure_skill(can_name, category)
                        skill_data[can_name]["interview_scores"].append(score_val)
                        skill_data[can_name]["interview_attempts"] += 1
                        skill_data[can_name]["sources"].append(f"interview_{interview.id}")
        elif interview.score is not None:
            # Fallback to overall interview score distributed to role skills
            role_skills = _infer_skills_from_text(interview.job_role)
            if not role_skills:
                can_role, cat = normalize_skill_name(interview.job_role)
                role_skills = [(can_role, cat)]
            for can_name, category in role_skills:
                _ensure_skill(can_name, category)
                skill_data[can_name]["interview_scores"].append(float(interview.score))
                skill_data[can_name]["interview_attempts"] += 1
                skill_data[can_name]["sources"].append(f"interview_{interview.id}")

    # -------------------------------------------------------------
    # 3. Extract performance from Coding Submissions
    # -------------------------------------------------------------
    subs_res = await db.execute(
        select(CodingSubmission, CodingProblem)
        .join(CodingProblem, CodingSubmission.problem_id == CodingProblem.id)
        .where(CodingSubmission.user_id == user_id)
        .order_by(CodingSubmission.created_at.desc())
    )
    submissions = subs_res.all()

    for sub, prob in submissions:
        can_name, category = normalize_skill_name(prob.topic)
        _ensure_skill(can_name, category)

        # Score determination: "Accepted" is 100%, else graded score or test percentage
        if sub.status == "Accepted":
            sub_score = 100.0
        elif sub.total_tests > 0:
            sub_score = (sub.passed_tests / sub.total_tests) * 100.0
        else:
            sub_score = float(sub.score or 0.0)

        skill_data[can_name]["coding_scores"].append(sub_score)
        skill_data[can_name]["coding_attempts"] += 1
        skill_data[can_name]["sources"].append(f"coding_{prob.slug}")

    # -------------------------------------------------------------
    # 4. Compute Normalized Scores, Confidence, and Status
    # -------------------------------------------------------------
    computed_skills: dict[str, dict[str, Any]] = {}

    for canonical, info in skill_data.items():
        interview_scores = info["interview_scores"]
        coding_scores = info["coding_scores"]
        int_attempts = info["interview_attempts"]
        cod_attempts = info["coding_attempts"]
        total_attempts = int_attempts + cod_attempts

        avg_interview = (
            round(sum(interview_scores) / len(interview_scores), 1)
            if interview_scores
            else None
        )
        avg_coding = (
            round(sum(coding_scores) / len(coding_scores), 1)
            if coding_scores
            else None
        )

        # Combined calculation
        if avg_interview is not None and avg_coding is not None:
            # Weighted average
            combined = round((avg_interview * 0.5) + (avg_coding * 0.5), 1)
        elif avg_interview is not None:
            combined = avg_interview
        elif avg_coding is not None:
            combined = avg_coding
        else:
            combined = None

        # Confidence calculation
        if total_attempts >= thresholds.high_confidence_attempts:
            confidence = "high"
        elif total_attempts >= thresholds.medium_confidence_attempts:
            confidence = "medium"
        elif total_attempts >= 1:
            confidence = "low"
        else:
            confidence = "insufficient"

        # Status calculation
        if combined is None:
            status = "unassessed"
        elif combined < thresholds.weak_threshold:
            status = "weak"
        elif combined < thresholds.needs_practice_threshold:
            status = "needs_practice"
        else:
            status = "strong"

        # Determine explicit reason
        reason_parts = []
        if avg_interview is not None:
            reason_parts.append(
                f"Interview avg: {avg_interview}/100 across {int_attempts} attempt{'s' if int_attempts != 1 else ''}"
            )
        if avg_coding is not None:
            reason_parts.append(
                f"Coding avg: {avg_coding}/100 across {cod_attempts} submission{'s' if cod_attempts != 1 else ''}"
            )
        if not reason_parts:
            reason = "Skill identified from profile/resume; no direct technical assessments completed yet."
        else:
            reason = " | ".join(reason_parts)

        computed_skills[canonical] = {
            "canonical_skill": canonical,
            "category": info["category"],
            "interview_score": avg_interview,
            "interview_attempts": int_attempts,
            "coding_score": avg_coding,
            "coding_attempts": cod_attempts,
            "combined_score": combined,
            "total_attempts": total_attempts,
            "status": status,
            "confidence": confidence,
            "reason": reason,
        }

    return computed_skills


async def sync_and_persist_skill_performances(
    db: AsyncSession,
    user_id: uuid.UUID,
    thresholds: ThresholdConfig = DEFAULT_THRESHOLDS,
) -> list[SkillPerformance]:
    """
    Calculates candidate skills and updates the database records in skill_performances.
    """
    eval_results = await evaluate_user_skills(db, user_id, thresholds)
    now = datetime.now(timezone.utc)

    # Fetch existing skill records
    existing_res = await db.execute(
        select(SkillPerformance).where(SkillPerformance.user_id == user_id)
    )
    existing_map = {sp.canonical_skill: sp for sp in existing_res.scalars().all()}

    updated_records: list[SkillPerformance] = []

    for canonical, metrics in eval_results.items():
        score_val = metrics["combined_score"]
        sp = existing_map.get(canonical)

        if not sp:
            sp = SkillPerformance(
                user_id=user_id,
                canonical_skill=canonical,
                category=metrics["category"],
                interview_score=metrics["interview_score"],
                interview_attempts=metrics["interview_attempts"],
                coding_score=metrics["coding_score"],
                coding_attempts=metrics["coding_attempts"],
                combined_score=score_val,
                total_attempts=metrics["total_attempts"],
                status=metrics["status"],
                confidence=metrics["confidence"],
                last_assessed_at=now if score_val is not None else None,
                score_history=[
                    {
                        "date": now.isoformat(),
                        "score": score_val,
                        "status": metrics["status"],
                    }
                ] if score_val is not None else [],
            )
            db.add(sp)
        else:
            sp.category = metrics["category"]
            sp.interview_score = metrics["interview_score"]
            sp.interview_attempts = metrics["interview_attempts"]
            sp.coding_score = metrics["coding_score"]
            sp.coding_attempts = metrics["coding_attempts"]
            sp.combined_score = score_val
            sp.total_attempts = metrics["total_attempts"]
            sp.status = metrics["status"]
            sp.confidence = metrics["confidence"]
            if score_val is not None:
                sp.last_assessed_at = now
                history = list(sp.score_history or [])
                history.append(
                    {
                        "date": now.isoformat(),
                        "score": score_val,
                        "status": metrics["status"],
                    }
                )
                sp.score_history = history[-20:]  # Keep last 20 snapshots

        updated_records.append(sp)

    await db.commit()
    return updated_records
