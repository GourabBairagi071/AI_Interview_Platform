import asyncio
import datetime
import sys
sys.path.insert(0, ".")
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.coding.contest_model import Contest

async def refresh_live():
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Contest).where(Contest.slug == 'live-weekly-coding-clash-42'))
        c = r.scalar_one_or_none()
        if c:
            now = datetime.datetime.now(datetime.timezone.utc)
            c.start_time = now - datetime.timedelta(minutes=15)
            c.end_time = now + datetime.timedelta(hours=4)
            c.status = 'LIVE'
            await session.commit()
            print("Successfully refreshed live contest time window.")

if __name__ == "__main__":
    asyncio.run(refresh_live())
