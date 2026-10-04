import json
import re
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.schema import (
    AnalyticsOverviewResponse,
    DifficultyPerformance,
    InterviewHistoryItem,
    OverallPerformance,
    ScoreHistoryItem,
    TopicPerformance,
)
from app.modules.interview.model import Interview


def _parse_json_safely(value: str | None) -> list | dict | None:
    if not value or not value.strip():
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _clean_bullet(text: str) -> str:
    cleaned = re.sub(r"^[-•*–—\d.)\s]+", "", text).strip()
    return cleaned.strip("\"' ")


def _parse_string_list(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    parsed = _parse_json_safely(value)
    if isinstance(parsed, list):
        items = []
        for x in parsed:
            if isinstance(x, str):
                cleaned = _clean_bullet(x)
                if cleaned:
                    items.append(cleaned)
            elif isinstance(x, dict) and "text" in x:
                cleaned = _clean_bullet(str(x["text"]))
                if cleaned:
                    items.append(cleaned)
        return items
    # Plain text lines
    lines = value.split("\n")
    items = []
    for line in lines:
        cleaned = _clean_bullet(line)
        if cleaned:
            items.append(cleaned)
    return items


def _count_answered_questions(answers: str | None, questions_count: int) -> int:
    if not answers or not answers.strip():
        return 0

    parsed = _parse_json_safely(answers)
    if isinstance(parsed, list):
        count = 0
        for item in parsed:
            if isinstance(item, dict):
                text_val = item.get("text") or item.get("answer") or ""
                if str(text_val).strip() and str(text_val).strip().lower() != "no answer provided":
                    count += 1
            elif isinstance(item, str) and item.strip() and item.strip().lower() != "no answer provided":
                count += 1
        return count

    # Plain text format
    blocks = re.split(r"\n\n(?=Question\s+\d+:|\d+\.)", answers.strip())
    if blocks:
        valid_blocks = 0
        for b in blocks:
            # Check if has text beyond the question label
            sublines = [line.strip() for line in b.split("\n") if line.strip()]
            content_lines = [
                line for line in sublines
                if not re.match(r"^Question\s+\d+.*:$|^\d+\.", line, re.IGNORECASE)
                and line.lower() != "no answer provided"
            ]
            if content_lines:
                valid_blocks += 1
        if valid_blocks > 0:
            return valid_blocks

    return questions_count


async def get_user_analytics_overview(
    db: AsyncSession,
    user_id: UUID,
) -> AnalyticsOverviewResponse:
    # 1. Fetch all interviews for this user ordered chronologically
    stmt = (
        select(Interview)
        .where(Interview.user_id == user_id)
        .order_by(Interview.created_at.asc())
    )
    result = await db.execute(stmt)
    interviews = result.scalars().all()

    total_interviews = len(interviews)

    # 2. Filter completed interviews with valid scores
    completed_interviews = [i for i in interviews if i.status == "completed"]
    completed_with_scores = [i for i in completed_interviews if i.score is not None]

    # Calculate overall metrics
    overall_score = None
    best_score = None
    recent_score = None
    score_change = None
    score_change_direction = None

    if completed_with_scores:
        scores = [float(i.score) for i in completed_with_scores]
        overall_score = round(sum(scores) / len(scores), 1)
        best_score = round(max(scores), 1)
        recent_score = round(scores[-1], 1)

        if len(scores) >= 2:
            diff = round(scores[-1] - scores[-2], 1)
            score_change = diff
            score_change_direction = "up" if diff > 0 else "down" if diff < 0 else "neutral"

    # 3. Calculate total questions answered
    total_questions_answered = 0
    for i in interviews:
        q_count = 0
        parsed_q = _parse_json_safely(i.questions)
        if isinstance(parsed_q, list):
            q_count = len(parsed_q)
        total_questions_answered += _count_answered_questions(i.answers, q_count)

    # 4. Score History (chronological)
    score_history: list[ScoreHistoryItem] = []
    for i in completed_with_scores:
        dt = i.completed_at or i.created_at
        score_history.append(
            ScoreHistoryItem(
                interview_id=str(i.id),
                date=dt.strftime("%b %d, %Y") if dt else "—",
                role=i.job_role or "Technical Interview",
                score=round(float(i.score), 1),
                difficulty=(i.difficulty or "Medium").capitalize(),
            )
        )

    # 5. Topic Performance & Difficulty Performance
    topic_data: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    difficulty_data: dict[str, list[float]] = {
        "Easy": [],
        "Medium": [],
        "Hard": [],
    }

    # Also collect strengths, weaknesses, recommendations
    collected_strengths: list[str] = []
    collected_weaknesses: list[str] = []
    collected_recommendations: list[str] = []

    for i in completed_with_scores:
        parsed_q = _parse_json_safely(i.questions)
        parsed_eval = _parse_json_safely(i.question_evaluations)

        # Build map of evaluations if present
        eval_by_num: dict[int, dict] = {}
        if isinstance(parsed_eval, list):
            for idx, ev in enumerate(parsed_eval, start=1):
                if isinstance(ev, dict):
                    q_num = ev.get("question_number", idx)
                    if isinstance(q_num, int):
                        eval_by_num[q_num] = ev

        session_date = i.completed_at or i.created_at or datetime.utcnow()
        session_diff = (i.difficulty or "Medium").capitalize()
        if session_diff not in difficulty_data:
            session_diff = "Medium"

        if isinstance(parsed_q, list) and len(parsed_q) > 0:
            for idx, q_item in enumerate(parsed_q, start=1):
                q_topic = "General"
                q_diff = session_diff

                if isinstance(q_item, dict):
                    raw_topic = q_item.get("topic")
                    if raw_topic and str(raw_topic).strip():
                        q_topic = str(raw_topic).strip().title()
                    raw_diff = q_item.get("difficulty")
                    if raw_diff and str(raw_diff).capitalize() in difficulty_data:
                        q_diff = str(raw_diff).capitalize()
                elif isinstance(q_item, str):
                    q_topic = (i.job_role or "Technical").strip().title()

                # Get score for this question
                q_score = None
                if idx in eval_by_num:
                    s_val = eval_by_num[idx].get("score")
                    if s_val is not None:
                        try:
                            q_score = float(s_val)
                        except (ValueError, TypeError):
                            q_score = None

                if q_score is None:
                    q_score = float(i.score)

                topic_data[q_topic].append((session_date, q_score))
                difficulty_data[q_diff].append(q_score)
        else:
            # Fallback to role as topic
            role_topic = (i.job_role or "General").strip().title()
            topic_data[role_topic].append((session_date, float(i.score)))
            difficulty_data[session_diff].append(float(i.score))

        # Stored strengths
        for s in _parse_string_list(i.strengths):
            if s and s not in collected_strengths:
                collected_strengths.append(s)

        # Stored weaknesses
        for w in _parse_string_list(i.weaknesses):
            if w and w not in collected_weaknesses:
                collected_weaknesses.append(w)

        # AI feedback recommendations
        if i.feedback and i.feedback.strip():
            # Extract actionable feedback sentences
            sentences = re.split(r"(?<=[.!?])\s+", i.feedback.strip())
            for sent in sentences:
                sent_clean = sent.strip()
                if any(
                    kw in sent_clean.lower()
                    for kw in [
                        "recommend",
                        "improve",
                        "focus on",
                        "enhance",
                        "practice",
                        "consider",
                        "deepen",
                        "review",
                        "strengthen",
                        "work on",
                        "suggest",
                        "prepare",
                    ]
                ) and len(sent_clean) >= 20:
                    if sent_clean not in collected_recommendations:
                        collected_recommendations.append(sent_clean)

    # Build topic performance list
    topic_performance: list[TopicPerformance] = []
    for topic, score_entries in topic_data.items():
        if not score_entries:
            continue
        scores = [s for _, s in score_entries]
        avg_score = round(sum(scores) / len(scores), 1)
        count = len(scores)

        # Trend calculation
        if count >= 2:
            sorted_entries = sorted(score_entries, key=lambda x: x[0])
            sorted_scores = [s for _, s in sorted_entries]
            mid = count // 2
            first_half = sorted_scores[:mid]
            second_half = sorted_scores[mid:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            diff = second_avg - first_avg
            if diff >= 3.0:
                trend = "improving"
            elif diff <= -3.0:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        topic_performance.append(
            TopicPerformance(
                topic=topic,
                average_score=avg_score,
                question_count=count,
                trend=trend,
            )
        )

        # If strong topic and high count, enrich strengths
        if avg_score >= 80.0 and count >= 2:
            derived_strength = f"Consistently strong in {topic} (Avg: {avg_score}%)"
            if derived_strength not in collected_strengths:
                collected_strengths.append(derived_strength)

        # If weaker topic and high count, enrich weaknesses
        if avg_score < 70.0 and count >= 2:
            derived_weakness = f"Room for improvement in {topic} (Avg: {avg_score}%)"
            if derived_weakness not in collected_weaknesses:
                collected_weaknesses.append(derived_weakness)

    # Sort topics by question count desc, then average score desc
    topic_performance.sort(key=lambda t: (-t.question_count, -t.average_score))

    # Build difficulty performance list
    difficulty_performance: list[DifficultyPerformance] = []
    for diff_name in ["Easy", "Medium", "Hard"]:
        diff_scores = difficulty_data.get(diff_name, [])
        if diff_scores:
            avg = round(sum(diff_scores) / len(diff_scores), 1)
            cnt = len(diff_scores)
        else:
            avg = None
            cnt = 0
        difficulty_performance.append(
            DifficultyPerformance(
                difficulty=diff_name,
                average_score=avg,
                question_count=cnt,
            )
        )

    # Deduplicate strengths, weaknesses, recommendations
    def _dedupe_list(items: list[str]) -> list[str]:
        seen = set()
        deduped = []
        for it in items:
            normalized = it.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(it.strip())
        return deduped

    final_strengths = _dedupe_list(collected_strengths)[:8]
    final_weaknesses = _dedupe_list(collected_weaknesses)[:8]
    final_recommendations = _dedupe_list(collected_recommendations)[:8]

    # If no separate feedback sentences found, use stored weaknesses as recommendations
    if not final_recommendations and final_weaknesses:
        final_recommendations = [f"Focus on addressing: {w}" for w in final_weaknesses[:5]]

    # 6. Interview History (all sessions, newest first)
    interview_history: list[InterviewHistoryItem] = []
    for i in reversed(interviews):
        parsed_q = _parse_json_safely(i.questions)
        q_count = len(parsed_q) if isinstance(parsed_q, list) else 0

        route = f"/results/{i.id}" if i.status == "completed" else f"/interview/{i.id}"
        dt = i.created_at

        interview_history.append(
            InterviewHistoryItem(
                interview_id=str(i.id),
                date=dt.strftime("%b %d, %Y") if dt else "—",
                role=i.job_role or "Technical Interview",
                score=round(float(i.score), 1) if i.score is not None else None,
                difficulty=(i.difficulty or "Medium").capitalize(),
                status=i.status.lower(),
                total_questions=q_count,
                result_route=route,
            )
        )

    return AnalyticsOverviewResponse(
        overall=OverallPerformance(
            overall_score=overall_score,
            best_score=best_score,
            recent_score=recent_score,
            total_interviews=total_interviews,
            completed_interviews=len(completed_interviews),
            total_questions_answered=total_questions_answered,
            score_change=score_change,
            score_change_direction=score_change_direction,
        ),
        score_history=score_history,
        topic_performance=topic_performance,
        difficulty_performance=difficulty_performance,
        strengths=final_strengths,
        weaknesses=final_weaknesses,
        recommendations=final_recommendations,
        interview_history=interview_history,
    )
