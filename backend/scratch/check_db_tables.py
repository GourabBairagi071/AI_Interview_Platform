import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
import json
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def run():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = sorted([r[0] for r in res.fetchall()])
        print("DB Tables:", tables)
        for t in tables:
            try:
                c = (await session.execute(text(f'SELECT count(*) FROM "{t}"'))).scalar()
                print(f"{t}: {c}")
            except Exception as e:
                await session.rollback()
                print(f"{t}: ERROR ({e})")

if __name__ == "__main__":
    asyncio.run(run())
