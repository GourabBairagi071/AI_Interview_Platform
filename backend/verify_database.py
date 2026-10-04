import asyncio
import json
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.modules.coding.model import CodingProblem

async def verify():
    async with AsyncSessionLocal() as db:
        # 1. Total count
        total_count = (await db.execute(select(func.count()).select_from(CodingProblem))).scalar()
        print('========================================')
        print(f'1. TOTAL PROBLEM COUNT: {total_count}')
        print('========================================')
        assert total_count == 1000, f'Expected 1000, got {total_count}'

        # 2. Difficulty counts
        diff_stmt = select(CodingProblem.difficulty, func.count()).group_by(CodingProblem.difficulty)
        diff_counts = dict((await db.execute(diff_stmt)).fetchall())
        print('\n2. DIFFICULTY COUNTS:')
        for d, c in sorted(diff_counts.items()):
            print(f'   {d}: {c}')
        print(f'   Total: {sum(diff_counts.values())}')
        assert diff_counts.get('Easy') == 300, f"Expected 300 Easy, got {diff_counts.get('Easy')}"
        assert diff_counts.get('Medium') == 500, f"Expected 500 Medium, got {diff_counts.get('Medium')}"
        assert diff_counts.get('Hard') == 200, f"Expected 200 Hard, got {diff_counts.get('Hard')}"

        # 3. Topic counts
        topic_stmt = select(CodingProblem.topic, func.count()).group_by(CodingProblem.topic).order_by(CodingProblem.topic)
        topic_counts = (await db.execute(topic_stmt)).fetchall()
        print(f'\n3. TOPIC COUNTS ({len(topic_counts)} distinct topics):')
        for t, c in topic_counts:
            print(f'   {t}: {c}')

        # 4. Duplicate slugs
        slug_dup_stmt = select(CodingProblem.slug, func.count()).group_by(CodingProblem.slug).having(func.count() > 1)
        dup_slugs = (await db.execute(slug_dup_stmt)).fetchall()
        print(f'\n4. DUPLICATE SLUGS: {len(dup_slugs)}')
        assert len(dup_slugs) == 0, f'Duplicate slugs found: {dup_slugs}'

        # 5. Duplicate titles
        title_dup_stmt = select(CodingProblem.title, func.count()).group_by(CodingProblem.title).having(func.count() > 1)
        dup_titles = (await db.execute(title_dup_stmt)).fetchall()
        print(f'5. DUPLICATE TITLES: {len(dup_titles)}')
        assert len(dup_titles) == 0, f'Duplicate titles found: {dup_titles}'

        # 6. Missing descriptions
        missing_desc_stmt = select(func.count()).select_from(CodingProblem).where((CodingProblem.description == None) | (CodingProblem.description == ''))
        missing_desc = (await db.execute(missing_desc_stmt)).scalar()
        print(f'6. MISSING DESCRIPTIONS: {missing_desc}')
        assert missing_desc == 0

        # 7. Missing starter codes
        missing_starter_stmt = select(func.count()).select_from(CodingProblem).where((CodingProblem.starter_code == None) | (CodingProblem.starter_code == ''))
        missing_starter = (await db.execute(missing_starter_stmt)).scalar()
        print(f'7. MISSING STARTER CODE: {missing_starter}')
        assert missing_starter == 0

        # 8. Missing tests
        missing_tests_stmt = select(func.count()).select_from(CodingProblem).where((CodingProblem.test_cases == None) | (CodingProblem.test_cases == ''))
        missing_tests = (await db.execute(missing_tests_stmt)).scalar()
        print(f'8. MISSING PUBLIC TESTS: {missing_tests}')
        assert missing_tests == 0

        missing_hidden_stmt = select(func.count()).select_from(CodingProblem).where((CodingProblem.hidden_test_cases == None) | (CodingProblem.hidden_test_cases == ''))
        missing_hidden = (await db.execute(missing_hidden_stmt)).scalar()
        print(f'8b. MISSING HIDDEN TESTS: {missing_hidden}')
        assert missing_hidden == 0

        # 9. Invalid difficulty values
        invalid_diff_stmt = select(func.count()).select_from(CodingProblem).where(~CodingProblem.difficulty.in_(['Easy', 'Medium', 'Hard']))
        invalid_diff = (await db.execute(invalid_diff_stmt)).scalar()
        print(f'9. INVALID DIFFICULTY VALUES: {invalid_diff}')
        assert invalid_diff == 0

        # 10. Sample verification of 4 supported languages in starter_code
        sample_stmt = select(CodingProblem.title, CodingProblem.starter_code).limit(20)
        samples = (await db.execute(sample_stmt)).fetchall()
        for title, sc_json in samples:
            sc = json.loads(sc_json)
            for lang in ['python', 'javascript', 'cpp', 'java']:
                assert lang in sc, f'{title} missing starter code for {lang}'
        print('\n10. STARTER CODE SAMPLE INTEGRITY: Verified all 4 languages (python, javascript, cpp, java) present and well-formed.')

        print('\nALL DATABASE INTEGRITY CHECKS PASSED PERFECTLY!')

if __name__ == '__main__':
    asyncio.run(verify())
