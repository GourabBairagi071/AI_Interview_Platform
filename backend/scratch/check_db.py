import sys
sys.path.insert(0, ".")
import asyncio
import json
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT transcript, question_evaluations 
            FROM interviews 
            WHERE id = 'd06c56a2-6b7f-4955-8c27-01e03091899e'
        """))
        row = result.fetchone()
        if row:
            print("Transcript:")
            print(json.dumps(json.loads(row[0]), indent=2))
            if row[1]:
                print("Question evaluations:")
                print(json.dumps(json.loads(row[1]), indent=2))

asyncio.run(run())
