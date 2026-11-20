import asyncio
import sys
sys.path.insert(0, '.')
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = [row[0] for row in res.fetchall()]
        print(f"TOTAL PUBLIC TABLES: {len(tables)}")
        for t in tables:
            print(f"  - {t}")

asyncio.run(main())
