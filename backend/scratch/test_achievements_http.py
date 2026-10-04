import asyncio
import os
import sys
import urllib.request
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.security import create_access_token
from app.core.database import AsyncSessionLocal
from app.modules.auth.model import User
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalars().first()
        assert user is not None
        token = create_access_token(str(user.id))

    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/achievements
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/achievements", headers=headers)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print(f"[PASS] HTTP GET /api/v1/achievements: status={resp.status}, total={data['total']}, unlocked={data['unlocked_count']}")

    # 2. GET /api/v1/achievements/summary
    req2 = urllib.request.Request("http://127.0.0.1:8000/api/v1/achievements/summary", headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        assert resp2.status == 200
        data2 = json.loads(resp2.read().decode())
        print(f"[PASS] HTTP GET /api/v1/achievements/summary: status={resp2.status}, categories={len(data2['categories'])}, total_xp={data2['total_xp_earned']}")

    # 3. GET /api/v1/achievements/{id}
    req3 = urllib.request.Request("http://127.0.0.1:8000/api/v1/achievements/first_solve", headers=headers)
    with urllib.request.urlopen(req3) as resp3:
        assert resp3.status == 200
        data3 = json.loads(resp3.read().decode())
        print(f"[PASS] HTTP GET /api/v1/achievements/first_solve: status={resp3.status}, name='{data3['achievement']['name']}'")

    print("[PASS] ALL HTTP ENDPOINTS FUNCTIONING HEALTHILY!")


if __name__ == "__main__":
    asyncio.run(main())
