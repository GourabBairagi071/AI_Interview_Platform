import asyncio
import json
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.modules.auth.model import User
from app.modules.coding.model import CodingProblem
from app.modules.coding.execution import CodeExecutionService

BASE_URL = "http://127.0.0.1:8000"

async def test_backend_apis():
    print("\n==================================================")
    print("BACKEND API & EXECUTION VERIFICATION (1,000 PROBLEMS)")
    print("==================================================")

    # 1. Fetch a user for authenticated endpoints
    async with AsyncSessionLocal() as db:
        user_stmt = select(User).limit(1)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        assert user is not None, "No user found in database for authentication test"
        token = create_access_token(str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. Test /api/v1/coding/problems with pagination
        r = await client.get("/api/v1/coding/problems?page=1&page_size=10")
        assert r.status_code == 200, f"Failed /coding/problems: {r.status_code}"
        data = r.json()
        print(f"1. Pagination (page 1, size 10): Returned {len(data['items'])} items, Total items: {data['total']}")
        assert data['total'] == 1000, f"Expected total 1000, got {data['total']}"
        assert len(data['items']) == 10, f"Expected 10 items, got {len(data['items'])}"

        # 2. Test Search
        r = await client.get("/api/v1/coding/problems?search=Prefix+Sum&page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        print(f"2. Search ('Prefix Sum'): Found {data['total']} matching problems. First: {data['items'][0]['title']}")
        assert data['total'] > 0

        # 3. Test Difficulty Filter: Easy (expect 300)
        r = await client.get("/api/v1/coding/problems?difficulty=Easy&page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        print(f"3. Difficulty Filter (Easy): Found {data['total']} problems (Expected 300)")
        assert data['total'] == 300, f"Expected 300 Easy, got {data['total']}"

        # 3b. Difficulty Filter: Medium (expect 500)
        r = await client.get("/api/v1/coding/problems?difficulty=Medium&page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        print(f"   Difficulty Filter (Medium): Found {data['total']} problems (Expected 500)")
        assert data['total'] == 500, f"Expected 500 Medium, got {data['total']}"

        # 3c. Difficulty Filter: Hard (expect 200)
        r = await client.get("/api/v1/coding/problems?difficulty=Hard&page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        print(f"   Difficulty Filter (Hard): Found {data['total']} problems (Expected 200)")
        assert data['total'] == 200, f"Expected 200 Hard, got {data['total']}"

        # 4. Test Topic Filter: Dynamic Programming
        r = await client.get("/api/v1/coding/problems?topic=Dynamic+Programming&page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        print(f"4. Topic Filter ('Dynamic Programming'): Found {data['total']} problems")
        assert data['total'] == 114

        # 5. Test Problem Detail & Confidentiality of Hidden Tests
        first_slug = data['items'][0]['slug']
        r = await client.get(f"/api/v1/coding/problems/{first_slug}")
        assert r.status_code == 200
        prob = r.json()
        print(f"5. Problem Detail: '{prob['title']}' (slug: {first_slug})")
        print(f"   Public test cases visible: {len(prob.get('test_cases', []))}")
        print(f"   Hidden test cases field present in public response: {'hidden_test_cases' in prob}")
        assert 'hidden_test_cases' not in prob, "CRITICAL: Hidden test cases leaked in public API response!"

        # 6. Test Leaderboard
        r = await client.get("/api/v1/coding/leaderboard?limit=10")
        assert r.status_code == 200
        leaderboard = r.json()
        print(f"6. Leaderboard: Returned {len(leaderboard.get('leaderboard', []))} rankings")

        # 7. Test Recommendations (Authenticated)
        r = await client.get("/api/v1/coding/recommendations?limit=5", headers=headers)
        assert r.status_code == 200, f"Recommendations error: {r.text}"
        recs = r.json()
        print(f"7. Recommendations: Returned {len(recs.get('recommendations', []))} personalized suggestions")

        # 8. Test Coding Statistics (Authenticated)
        r = await client.get("/api/v1/coding/stats", headers=headers)
        assert r.status_code == 200, f"Stats error: {r.text}"
        stats = r.json()
        print(f"8. Coding Statistics: Total solved={stats.get('total_solved', 0)}, acceptance={stats.get('acceptance_rate', 0)}%")

        # 9. Test Custom Input Run Endpoint
        custom_payload = {
            "problem_id": prob["id"],
            "language": "python",
            "source_code": "import sys\nline = sys.stdin.read().strip()\nprint(line.upper())\n",
            "custom_input": "interview platform custom test"
        }
        r = await client.post("/api/v1/coding/run-custom", json=custom_payload, headers=headers)
        assert r.status_code == 200, f"Custom run error: {r.text}"
        custom_res = r.json()
        print(f"9. Custom Input Execution: Output='{custom_res.get('stdout', '').strip()}', Success={custom_res.get('status') == 'success'}")
        assert "INTERVIEW PLATFORM CUSTOM TEST" in custom_res.get('stdout', '')

        # 10. Test AI Coding Assistant
        assist_payload = {
            "problem_id": prob["id"],
            "language": "python",
            "source_code": "def solve(): pass",
            "action": "give_hint",
            "hint_level": 1
        }
        r = await client.post("/api/v1/coding/assist", json=assist_payload, headers=headers)
        assert r.status_code == 200, f"AI assist error: {r.text}"
        assist_res = r.json()
        print(f"10. AI Coding Assistant: Hint 1 received (Length: {len(assist_res.get('content', ''))} chars)")

    # 11. Test Execution Sandbox across diverse categories: Easy, Medium, Hard, Arrays, Trees, Graphs, DP, SQL, ML
    print("\n11. RUNNING EXECUTION TESTS ACROSS DIVERSE CATEGORIES & DIFFICULTIES:")
    execution_service = CodeExecutionService()

    async with AsyncSessionLocal() as db:
        topics_to_test = ["Arrays", "Trees", "Graphs", "Dynamic Programming", "SQL", "Data Science / ML"]
        for topic in topics_to_test:
            stmt = select(CodingProblem).where(CodingProblem.topic == topic).limit(1)
            p = (await db.execute(stmt)).scalar_one_or_none()
            if not p:
                continue

            # Parse test cases
            test_cases_list = json.loads(p.test_cases) if p.test_cases else []
            if not test_cases_list and p.examples:
                test_cases_list = json.loads(p.examples)

            sample_in = test_cases_list[0]["input"]
            expected_out = test_cases_list[0]["output"]

            # Provide working python snippet echoing expected_out
            test_py_code = f"""import sys
lines = sys.stdin.read().strip().splitlines()
print({repr(expected_out)})
"""
            res = await execution_service.execute_test_cases(
                language="python",
                source_code=test_py_code,
                test_cases=[{"input": sample_in, "output": expected_out}]
            )
            passed = (res.get("status") == "Accepted" and res.get("total_passed") == len(res.get("results", [])))
            runtime = res.get("results", [{}])[0].get("execution_time", 0.0)
            print(f"   [{p.difficulty}] {p.topic} -> '{p.title}': Status={res.get('status')}, Passed={passed}, Time={runtime:.1f}ms")
            assert passed, f"Execution failed for {p.title}: {res}"

    print("\nALL 11 BACKEND API & EXECUTION TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    asyncio.run(test_backend_apis())
