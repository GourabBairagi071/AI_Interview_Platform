import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'skills'"))
        print("COL TYPE:", res.all())
        sample = await db.execute(text("SELECT skills FROM user_profiles WHERE skills IS NOT NULL LIMIT 5"))
        print("SAMPLES:", sample.all())

if __name__ == "__main__":
    asyncio.run(main())
