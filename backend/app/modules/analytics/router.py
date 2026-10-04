from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics.schema import AnalyticsOverviewResponse
from app.modules.analytics.service import get_user_analytics_overview
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
)
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_analytics_overview(
        db=db,
        user_id=current_user.id,
    )
