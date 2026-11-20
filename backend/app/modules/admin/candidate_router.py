import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_current_user
from app.modules.auth.model import User
from app.modules.admin.model import Company, SystemSetting
from app.modules.admin.service import AdminService

router = APIRouter(
    tags=["Candidate Experience & Platform Settings"],
)


@router.get(
    "/dashboard/config",
    summary="Get candidate dashboard module visibility configuration",
)
async def get_candidate_dashboard_config(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Returns safe UI section visibility toggles controlled by platform administrators."""
    return await AdminService.get_dashboard_config(db)


@router.get(
    "/dashboard/featured",
    summary="Get aggregated featured content across contests, practice, coding, and roadmaps",
)
async def get_candidate_featured_content(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Returns active featured spotlight cards directly from PostgreSQL."""
    return await AdminService.get_featured_content(db)


@router.get(
    "/dashboard/summary",
    summary="Aggregated candidate dashboard summary for instant single-request loading",
)
async def get_candidate_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidates readiness score, ATS, weak topics, daily plan, upcoming contest, coding, achievements, and notifications."""
    return await AdminService.get_candidate_dashboard_summary(db, current_user.id)


@router.get(
    "/companies",
    summary="List companies and hiring patterns for candidate interview preparation",
)
async def list_candidate_companies(
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Lists published companies with interview patterns and preparation topic guides."""
    query = select(Company).where(Company.is_active.is_(True))
    if industry:
        query = query.where(Company.industry.ilike(f"%{industry}%"))
    if search:
        query = query.where(Company.name.ilike(f"%{search}%"))

    query = query.order_by(Company.name.asc()).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(query)
    companies = res.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "industry": c.industry,
            "logo_url": c.logo_url,
            "website": c.website,
            "roles": c.roles or [],
            "interview_patterns": c.interview_patterns or [],
            "technical_topics": c.technical_topics or [],
            "hr_topics": c.hr_topics or [],
            "coding_topics": c.coding_topics or [],
            "is_featured": c.is_featured,
        }
        for c in companies
    ]


@router.get(
    "/companies/{company_id}",
    summary="Get full company interview preparation pack and FAQs",
)
async def get_candidate_company_detail(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    res = await db.execute(select(Company).where(Company.id == company_id, Company.is_active.is_(True)))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found or inactive")
    return {
        "id": str(c.id),
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "industry": c.industry,
        "logo_url": c.logo_url,
        "website": c.website,
        "roles": c.roles or [],
        "interview_patterns": c.interview_patterns or [],
        "technical_topics": c.technical_topics or [],
        "hr_topics": c.hr_topics or [],
        "coding_topics": c.coding_topics or [],
        "faqs": c.faqs or [],
        "is_featured": c.is_featured,
    }


@router.get(
    "/platform/public-settings",
    summary="Get safe public platform settings for candidates",
)
async def get_public_platform_settings(
    db: AsyncSession = Depends(get_db),
):
    """Exposes only non-sensitive configuration values to clients."""
    res = await db.execute(select(SystemSetting).where(SystemSetting.is_sensitive.is_(False)))
    settings = res.scalars().all()
    return {
        s.key: s.value
        for s in settings
    }
