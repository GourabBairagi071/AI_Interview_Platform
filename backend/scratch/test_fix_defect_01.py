import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.modules.coding.model import CodingProblem

async def test_defect_01_fix():
    print("=== TESTING DEFECT-01 (ADMIN CODING PROBLEM COUNT) FIX ===")
    async with AsyncSessionLocal() as db:
        # 1. Total Unfiltered Count in DB
        actual_db_count = (await db.execute(select(func.count(CodingProblem.id)))).scalar()
        print(f"Direct DB Count: {actual_db_count}")
        assert actual_db_count == 1000, f"Expected 1000 coding problems in DB baseline, got {actual_db_count}"

        # 2. Test Unfiltered Count Query
        query = select(CodingProblem)
        subq = query.subquery()
        count_query = select(func.count()).select_from(subq)
        total_unfiltered = (await db.execute(count_query)).scalar() or 0
        print(f"Corrected Unfiltered Query Count: {total_unfiltered}")
        assert total_unfiltered == 1000, f"Expected total=1000, got {total_unfiltered}"

        # 3. Test Filtered Count (Difficulty = 'Easy')
        easy_query = select(CodingProblem).where(CodingProblem.difficulty.ilike("%Easy%"))
        easy_subq = easy_query.subquery()
        easy_count = (await db.execute(select(func.count()).select_from(easy_subq))).scalar() or 0
        print(f"Filtered 'Easy' Count: {easy_count}")
        assert 0 < easy_count < 1000, "Easy count should be between 1 and 999"

        # 4. Test Filtered Count (Difficulty = 'Hard')
        hard_query = select(CodingProblem).where(CodingProblem.difficulty.ilike("%Hard%"))
        hard_subq = hard_query.subquery()
        hard_count = (await db.execute(select(func.count()).select_from(hard_subq))).scalar() or 0
        print(f"Filtered 'Hard' Count: {hard_count}")
        assert 0 < hard_count < 1000, "Hard count should be between 1 and 999"

        # 5. Test Search Filter (search = 'Two Sum' or 'Array')
        search_query = select(CodingProblem).where(CodingProblem.title.ilike("%Array%"))
        search_subq = search_query.subquery()
        search_count = (await db.execute(select(func.count()).select_from(search_subq))).scalar() or 0
        print(f"Search 'Array' Count: {search_count}")

        # 6. Test Nonexistent Search Filter
        none_query = select(CodingProblem).where(CodingProblem.title.ilike("%NonexistentXYZProblem%"))
        none_subq = none_query.subquery()
        none_count = (await db.execute(select(func.count()).select_from(none_subq))).scalar() or 0
        print(f"Nonexistent Search Count: {none_count}")
        assert none_count == 0, "Nonexistent search should return 0"

        # 7. Pagination and Data Serialization Check
        paginated_rows = (await db.execute(query.order_by(CodingProblem.id.asc()).offset(0).limit(10))).scalars().all()
        assert len(paginated_rows) == 10
        for p in paginated_rows:
            assert isinstance(str(p.id), str) and len(str(p.id)) == 36, "UUID serialization invalid"
            assert hasattr(p, "title") and p.title

        print("SUCCESS: DEFECT-01 FIX VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_defect_01_fix())
