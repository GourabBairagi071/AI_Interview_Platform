import asyncio
import json
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User

BASE_URL = "http://127.0.0.1:8000"

async def test_contests():
    print("\n==================================================")
    print("COMPETITIVE CODING & CONTEST ARENA API VERIFICATION")
    print("==================================================")

    # 1. Fetch test user and generate JWT token
    async with AsyncSessionLocal() as db:
        user_stmt = select(User).limit(1)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        assert user is not None, "No user found in database"
        token = create_access_token(str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. List Contests
        r = await client.get("/api/v1/contests?status=ALL", headers=headers)
        assert r.status_code == 200, f"List contests failed: {r.status_code} {r.text}"
        data = r.json()
        contests = data.get("contests", [])
        print(f"1. List Contests: Found {len(contests)} contests. Total: {data.get('total')}")
        assert len(contests) >= 3, "Expected at least 3 seeded contests"

        live_contest = next((c for c in contests if c["status"] == "LIVE"), None)
        upcoming_contest = next((c for c in contests if c["status"] == "UPCOMING"), None)
        ended_contest = next((c for c in contests if c["status"] == "ENDED"), None)

        assert live_contest is not None, "Missing LIVE contest"
        assert upcoming_contest is not None, "Missing UPCOMING contest"
        assert ended_contest is not None, "Missing ENDED contest"

        print(f"   LIVE Contest:     '{live_contest['title']}' ({live_contest['slug']})")
        print(f"   UPCOMING Contest: '{upcoming_contest['title']}' ({upcoming_contest['slug']})")
        print(f"   ENDED Contest:    '{ended_contest['title']}' ({ended_contest['slug']})")

        # 2. Contest Details & Countdown
        r = await client.get(f"/api/v1/contests/{live_contest['slug']}", headers=headers)
        assert r.status_code == 200
        live_detail = r.json()
        print(f"\n2. Live Contest Details:")
        print(f"   Duration: {live_detail['duration_minutes']} mins, Server Time Remaining: {live_detail['time_remaining_seconds']}s")
        print(f"   Problems Count: {live_detail['problems_count']}")
        assert live_detail["time_remaining_seconds"] > 0, "Live contest should have remaining time"

        # 3. Upcoming Contest Problem Security Check (Locked!)
        r = await client.get(f"/api/v1/contests/{upcoming_contest['id']}/problems", headers=headers)
        print(f"\n3. Upcoming Contest Access Control (Expected 403 Forbidden):")
        print(f"   Status code: {r.status_code} ({r.json().get('detail')})")
        assert r.status_code == 403, "Upcoming contest problems must be locked!"

        # 4. Register for Live Contest
        r = await client.post(f"/api/v1/contests/{live_contest['id']}/register", headers=headers)
        assert r.status_code == 200
        print(f"\n4. Registration Test: {r.json()}")

        # 4b. Prevent Duplicate Registration
        r = await client.post(f"/api/v1/contests/{live_contest['id']}/register", headers=headers)
        assert r.status_code == 200
        assert r.json().get("registered") is True

        # 5. Fetch Live Contest Problems (Unlocked!)
        r = await client.get(f"/api/v1/contests/{live_contest['id']}/problems", headers=headers)
        assert r.status_code == 200
        prob_set = r.json()
        problems = prob_set.get("problems", [])
        print(f"\n5. Live Contest Problems: Unlocked {len(problems)} challenges")
        for p in problems:
            print(f"   [{p['label']}] {p['title']} ({p['difficulty']}) - {p['points']} pts")
        assert len(problems) == 4, "Expected 4 problems in live contest"

        prob_a = problems[0]

        # 6. Fetch Problem Detail & Verify Hidden Tests Confidentiality
        r = await client.get(f"/api/v1/contests/{live_contest['id']}/problems/{prob_a['problem_id']}", headers=headers)
        assert r.status_code == 200
        p_data = r.json()
        print(f"\n6. Problem Detail Confidentiality Check:")
        print(f"   Title: '{p_data['title']}', Public Tests: {len(p_data.get('test_cases', []))}")
        print(f"   Hidden Tests in response: {'hidden_test_cases' in p_data}")
        assert "hidden_test_cases" not in p_data, "Hidden tests leaked in contest problem response!"

        # 7. Run Sample Code in Contest
        sample_tests = p_data.get("test_cases", [])
        expected_sample_out = sample_tests[0]["output"] if sample_tests else "test"
        sample_code = f"import sys\nlines = sys.stdin.read().strip().splitlines()\nprint({repr(expected_sample_out)})\n"

        r = await client.post(
            f"/api/v1/contests/{live_contest['id']}/run",
            json={
                "problem_id": prob_a["problem_id"],
                "language": "python",
                "source_code": sample_code,
            },
            headers=headers,
        )
        assert r.status_code == 200
        run_res = r.json()
        print(f"\n7. Contest Run Sample: Status={run_res.get('status')}, Passed={run_res.get('total_passed')}/{run_res.get('total_tests')}")

        # 8. Submit Contest Solution (ICPC Scoring)
        r = await client.post(
            f"/api/v1/contests/{live_contest['id']}/submit",
            json={
                "problem_id": prob_a["problem_id"],
                "language": "python",
                "source_code": sample_code,
            },
            headers=headers,
        )
        assert r.status_code == 200
        sub_res = r.json()
        print(f"\n8. Contest Submit Solution:")
        print(f"   Submission ID: {sub_res['submission_id']}")
        print(f"   Status: {sub_res['status']}")
        print(f"   Points Awarded: {sub_res['points_awarded']}")
        print(f"   Penalty Minutes: {sub_res['penalty_minutes']}")
        print(f"   Current Rank: {sub_res['current_rank']}")
        print(f"   Total Solved: {sub_res['total_solved']}")

        # 9. Live Contest Leaderboard
        r = await client.get(f"/api/v1/contests/{live_contest['id']}/leaderboard", headers=headers)
        assert r.status_code == 200
        lb = r.json()
        print(f"\n9. Live Contest Leaderboard:")
        print(f"   Total Participants: {lb['total_participants']}")
        for entry in lb["leaderboard"][:5]:
            print(f"   Rank #{entry['rank']}: {entry['username']} - Score: {entry['total_score']} pts, Solved: {entry['solved_count']}, Penalty: {entry['penalty_minutes']}m")

        # 10. User Contest Status
        r = await client.get(f"/api/v1/contests/{live_contest['id']}/my-status", headers=headers)
        assert r.status_code == 200
        status_data = r.json()
        print(f"\n10. User Contest Status:")
        print(f"    Registered: {status_data['registered']}, Rank: #{status_data['rank']}")
        print(f"    Submissions logged: {len(status_data['submissions'])}")

        # 11. Contest Results
        r = await client.get(f"/api/v1/contests/{live_contest['id']}/results", headers=headers)
        assert r.status_code == 200
        res_data = r.json()
        print(f"\n11. Contest Results:")
        print(f"    Final Rank: #{res_data['final_rank']}, Solved: {res_data['solved_count']}, Score: {res_data['total_score']}")

        # 12. User Contest History
        r = await client.get("/api/v1/contests/my-history", headers=headers)
        assert r.status_code == 200
        hist_data = r.json()
        print(f"\n12. User Contest History:")
        print(f"    Total Contests: {hist_data['total_contests']}, Best Rank: #{hist_data['best_rank']}, Total Solved: {hist_data['total_problems_solved']}")

    print("\n==================================================")
    print("ALL 12 CONTEST API INTEGRATION CHECKS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_contests())
