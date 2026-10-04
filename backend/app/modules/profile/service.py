from collections import defaultdict
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.model import User, UserProfile
from app.modules.interview.model import Interview
from app.modules.practice.model import PracticeProgress
from app.modules.practice.service import (
    load_all_platform_questions,
    _calculate_xp_from_records,
    _calculate_streak_from_records,
    _evaluate_mastery_from_records,
)
from app.modules.achievements.service import get_user_achievements_summary
from app.modules.resume.model import Resume
from app.modules.profile.schema import (
    AccountDetails,
    AchievementSummary,
    ComprehensiveProfileResponse,
    InterviewSummary,
    PracticeSummary,
    PracticeTechItem,
    ProfileDetails,
    ProfileUpdateRequest,
    RecentInterview,
    ResumeStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProfileService:
    @staticmethod
    async def get_or_create_user_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserProfile:
        res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = res.scalar_one_or_none()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        return profile

    @staticmethod
    async def get_comprehensive_profile(
        db: AsyncSession,
        current_user: User,
    ) -> ComprehensiveProfileResponse:
        user_id = current_user.id

        # 1. Profile Model
        profile = await ProfileService.get_or_create_user_profile(db, user_id)

        profile_details = ProfileDetails(
            id=str(profile.id),
            user_id=str(user_id),
            full_name=current_user.full_name or "Candidate",
            email=current_user.email,
            headline=profile.headline,
            bio=profile.bio,
            phone=profile.phone,
            location=profile.location,
            college=profile.college,
            degree=profile.degree,
            graduation_year=profile.graduation_year,
            target_role=profile.target_role,
            experience_level=profile.experience_level,
            skills=profile.skills,
            github_url=profile.github_url,
            linkedin_url=profile.linkedin_url,
            portfolio_url=profile.portfolio_url,
            avatar_url=profile.avatar_url,
            created_at=profile.created_at.isoformat() if profile.created_at else utc_now().isoformat(),
            updated_at=profile.updated_at.isoformat() if profile.updated_at else utc_now().isoformat(),
        )

        # 2. Account Details
        account_details = AccountDetails(
            id=str(user_id),
            email=current_user.email,
            is_verified=bool(current_user.is_verified),
            created_at=current_user.created_at.isoformat() if current_user.created_at else utc_now().isoformat(),
        )

        # 3. Practice Statistics
        catalog = await load_all_platform_questions(db)
        prog_stmt = select(PracticeProgress).where(PracticeProgress.user_id == user_id)
        prog_res = await db.execute(prog_stmt)
        records = list(prog_res.scalars().all())

        total_xp, xp_stats = _calculate_xp_from_records(catalog, records)
        streak_stats = _calculate_streak_from_records(records)
        mastery_stats = _evaluate_mastery_from_records(catalog, records)

        # Technologies practiced
        tech_totals: dict[str, int] = defaultdict(int)
        tech_solved: dict[str, int] = defaultdict(int)
        tech_slugs: dict[str, str] = {}
        solved_qids = {p.question_id for p in records if p.solved}

        for qid, q in catalog.items():
            tech = q.get("technology") or "General"
            tech_totals[tech] += 1
            tech_slugs[tech] = q.get("technology_slug") or tech.lower().replace(" ", "-")
            if qid in solved_qids:
                tech_solved[tech] += 1

        tech_items: list[PracticeTechItem] = []
        for tech, solved_count in tech_solved.items():
            if solved_count > 0:
                tot = tech_totals.get(tech, solved_count)
                pct = round((solved_count / tot) * 100, 1) if tot > 0 else 0.0
                tech_items.append(
                    PracticeTechItem(
                        technology=tech,
                        slug=tech_slugs.get(tech, tech.lower()),
                        solved=solved_count,
                        total=tot,
                        mastery_percentage=pct,
                    )
                )
        tech_items.sort(key=lambda t: t.solved, reverse=True)

        total_catalog = len(catalog)
        total_solved = len(solved_qids)
        comp_pct = round((total_solved / total_catalog) * 100, 1) if total_catalog > 0 else 0.0

        practice_summary = PracticeSummary(
            questions_solved=total_solved,
            total_questions=total_catalog,
            completion_percentage=comp_pct,
            current_streak=streak_stats.current_streak,
            longest_streak=streak_stats.longest_streak,
            total_xp=total_xp,
            current_level=xp_stats.level,
            level_title=xp_stats.level_title,
            progress_pct=xp_stats.progress_pct,
            topics_mastered=mastery_stats.mastered_topics,
            technologies_practiced=tech_items,
        )

        # 4. Achievements Summary
        ach_summary_res = await get_user_achievements_summary(db, user_id)
        recent_unlocks = [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "rarity": a.rarity,
                "xp_reward": a.xp_reward,
                "unlocked_at": a.unlocked_at,
            }
            for a in ach_summary_res.recent_unlocks
        ]

        achievement_summary = AchievementSummary(
            unlocked_count=ach_summary_res.unlocked_count,
            total_achievements=ach_summary_res.total_achievements,
            completion_percentage=ach_summary_res.completion_percentage,
            recent_unlocks=recent_unlocks,
        )

        # 5. Interview Summary
        int_stmt = (
            select(Interview)
            .where(Interview.user_id == user_id)
            .order_by(Interview.created_at.desc())
        )
        int_res = await db.execute(int_stmt)
        interviews = list(int_res.scalars().all())
        completed_interviews = [i for i in interviews if i.status == "completed"]

        scores = [float(i.score) for i in completed_interviews if i.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        best_score = round(max(scores), 1) if scores else 0.0

        recent_interview = None
        if completed_interviews:
            latest = completed_interviews[0]
            recent_interview = RecentInterview(
                id=str(latest.id),
                job_role=latest.job_role,
                difficulty=latest.difficulty,
                score=latest.score,
                completed_at=latest.completed_at.isoformat() if latest.completed_at else None,
            )

        interview_summary = InterviewSummary(
            completed_interviews=len(completed_interviews),
            average_score=avg_score,
            best_score=best_score,
            recent_interview=recent_interview,
        )

        # 6. Resume Status
        res_stmt = select(Resume).where(Resume.user_id == user_id)
        res_result = await db.execute(res_stmt)
        user_resume = res_result.scalar_one_or_none()

        resume_status = ResumeStatus(
            has_resume=user_resume is not None,
            filename=user_resume.filename if user_resume else None,
            uploaded_at=user_resume.uploaded_at.isoformat() if user_resume and user_resume.uploaded_at else None,
        )

        return ComprehensiveProfileResponse(
            profile=profile_details,
            account=account_details,
            practice_summary=practice_summary,
            achievement_summary=achievement_summary,
            interview_summary=interview_summary,
            resume_status=resume_status,
        )

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        current_user: User,
        data: ProfileUpdateRequest,
    ) -> ComprehensiveProfileResponse:
        user_id = current_user.id

        # Update full_name on User model if provided
        if data.full_name is not None and data.full_name.strip():
            current_user.full_name = data.full_name.strip()
            current_user.updated_at = utc_now()

        # Update fields on UserProfile
        profile = await ProfileService.get_or_create_user_profile(db, user_id)

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field != "full_name" and hasattr(profile, field):
                setattr(profile, field, value)

        profile.updated_at = utc_now()
        await db.commit()
        await db.refresh(profile)
        await db.refresh(current_user)

        return await ProfileService.get_comprehensive_profile(db, current_user)
