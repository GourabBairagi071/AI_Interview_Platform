import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'interview_question_vectors'
            ORDER BY ordinal_position;
        """))
        print("Columns in interview_question_vectors:")
        for row in res.fetchall():
            print(" -", row[0], ":", row[1])

if __name__ == "__main__":
    asyncio.run(check())
