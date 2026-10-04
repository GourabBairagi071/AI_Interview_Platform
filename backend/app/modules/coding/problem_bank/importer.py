import csv
import json
import logging
import os
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.coding.model import CodingProblem
from app.modules.coding.problem_bank.schema import ImportReport, ProblemRecord
from app.modules.coding.problem_bank.validator import ProblemValidator

logger = logging.getLogger(__name__)


class ProblemImporter:
    """Production-grade ingestion pipeline for bulk problem datasets."""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size

    def load_records_from_file(self, file_path: str) -> list[dict[str, Any]]:
        """Parses records from JSON, JSONL, or CSV file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        records: list[dict[str, Any]] = []

        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get("problems", data.get("items", [data]))

        elif ext in (".jsonl", ".ndjson"):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse json columns if present in csv
                    parsed_row: dict[str, Any] = {}
                    for k, v in row.items():
                        if not v:
                            parsed_row[k] = None
                            continue
                        trimmed = v.strip()
                        if trimmed.startswith(("{", "[")):
                            try:
                                parsed_row[k] = json.loads(trimmed)
                                continue
                            except Exception:
                                pass
                        parsed_row[k] = v
                    records.append(parsed_row)

        else:
            raise ValueError(f"Unsupported file format '{ext}'. Must be .json, .jsonl, or .csv")

        return records

    async def import_from_file(self, db: AsyncSession, file_path: str) -> ImportReport:
        """Parses and ingests a problem dataset file into PostgreSQL with transaction batching."""
        raw_records = self.load_records_from_file(file_path)
        return await self.import_records(db, raw_records)

    async def import_records(self, db: AsyncSession, records: list[dict[str, Any]]) -> ImportReport:
        """Validates, deduplicates, and batch-inserts problem records."""
        report = ImportReport(total_records=len(records))
        seen_slugs: set[str] = set()
        seen_titles: set[str] = set()

        valid_problems_to_insert: list[CodingProblem] = []

        for idx, raw in enumerate(records):
            try:
                # 1. Schema Parsing & Normalization
                problem_rec = ProblemRecord(**raw)
            except Exception as parse_err:
                report.invalid += 1
                report.errors.append(f"Record #{idx+1} schema error: {parse_err}")
                continue

            # 2. Content Validation
            is_valid, val_err = ProblemValidator.validate_problem_data(problem_rec)
            if not is_valid:
                report.invalid += 1
                report.errors.append(f"Record #{idx+1} ('{problem_rec.title}'): {val_err}")
                continue

            slug = problem_rec.slug or ""
            title = problem_rec.title.strip()

            # 3. Duplicate check within current batch
            if slug in seen_slugs or title.lower() in seen_titles:
                report.duplicates += 1
                continue

            # 4. Duplicate check against existing PostgreSQL database
            is_dup = await ProblemValidator.is_duplicate_in_db(db, slug, title)
            if is_dup:
                report.duplicates += 1
                continue

            seen_slugs.add(slug)
            seen_titles.add(title.lower())

            # 5. Format test cases & examples
            public_tests = problem_rec.public_test_cases
            if not public_tests and problem_rec.examples:
                public_tests = [
                    {"input": ex["input"], "output": ex["output"]}
                    for ex in problem_rec.examples if "input" in ex and "output" in ex
                ]

            constraints_str = (
                json.dumps(problem_rec.constraints)
                if isinstance(problem_rec.constraints, list)
                else (problem_rec.constraints or None)
            )

            # 6. Instantiate Database Model
            db_problem = CodingProblem(
                title=title,
                slug=slug,
                description=problem_rec.description,
                difficulty=problem_rec.difficulty,
                topic=problem_rec.topic,
                tags=json.dumps(problem_rec.tags) if problem_rec.tags else None,
                company_tags=json.dumps(problem_rec.company_tags) if problem_rec.company_tags else None,
                role_tags=json.dumps(problem_rec.role_tags) if problem_rec.role_tags else None,
                constraints=constraints_str,
                input_format=problem_rec.input_format,
                output_format=problem_rec.output_format,
                examples=json.dumps(problem_rec.examples) if problem_rec.examples else None,
                starter_code=json.dumps(problem_rec.starter_code) if problem_rec.starter_code else None,
                supported_languages=json.dumps(problem_rec.supported_languages),
                test_cases=json.dumps(public_tests) if public_tests else None,
                hidden_test_cases=json.dumps(problem_rec.hidden_test_cases) if problem_rec.hidden_test_cases else None,
                expected_time_complexity=problem_rec.expected_time_complexity,
                expected_space_complexity=problem_rec.expected_space_complexity,
                editorial=problem_rec.editorial,
                hints=json.dumps(problem_rec.hints) if problem_rec.hints else None,
            )

            valid_problems_to_insert.append(db_problem)

            # Batch commit when reaching batch size
            if len(valid_problems_to_insert) >= self.batch_size:
                try:
                    db.add_all(valid_problems_to_insert)
                    await db.commit()
                    report.imported += len(valid_problems_to_insert)
                    valid_problems_to_insert = []
                except Exception as commit_err:
                    await db.rollback()
                    report.failed += len(valid_problems_to_insert)
                    report.errors.append(f"Batch commit failure: {commit_err}")
                    valid_problems_to_insert = []

        # Flush any remaining records
        if valid_problems_to_insert:
            try:
                db.add_all(valid_problems_to_insert)
                await db.commit()
                report.imported += len(valid_problems_to_insert)
            except Exception as commit_err:
                await db.rollback()
                report.failed += len(valid_problems_to_insert)
                report.errors.append(f"Final batch commit failure: {commit_err}")

        return report
