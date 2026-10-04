import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.coding.model import CodingProblem
from app.modules.coding.problem_bank.schema import ProblemRecord

logger = logging.getLogger(__name__)


class ProblemValidator:
    @staticmethod
    def validate_problem_data(record: ProblemRecord) -> tuple[bool, str | None]:
        """Validates problem completeness and test consistency."""
        if not record.title or len(record.title.strip()) < 2:
            return False, "Title must be at least 2 characters long."

        if not record.description or len(record.description.strip()) < 10:
            return False, "Description must be at least 10 characters long."

        # Ensure we have test cases
        has_tests = bool(record.public_test_cases) or bool(record.examples)
        if not has_tests:
            return False, "Problem must contain at least one public test case or example."

        # Validate test case structure
        for i, tc in enumerate(record.public_test_cases):
            if "input" not in tc or "output" not in tc:
                return False, f"Public test case #{i+1} missing 'input' or 'output'."

        for i, tc in enumerate(record.hidden_test_cases):
            if "input" not in tc or "output" not in tc:
                return False, f"Hidden test case #{i+1} missing 'input' or 'output'."

        return True, None

    @staticmethod
    async def is_duplicate_in_db(db: AsyncSession, slug: str, title: str) -> bool:
        """Checks if a problem with the given slug or exact title already exists in PostgreSQL."""
        stmt = select(CodingProblem.id).where(
            (CodingProblem.slug == slug) | (CodingProblem.title == title)
        )
        res = await db.execute(stmt)
        return res.first() is not None
