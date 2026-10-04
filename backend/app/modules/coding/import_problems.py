import argparse
import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.database import AsyncSessionLocal
from app.modules.coding.problem_bank.importer import ProblemImporter


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest coding problems into PostgreSQL from JSON, JSONL, or CSV datasets."
    )
    parser.add_argument("file_path", help="Path to problem dataset (.json, .jsonl, or .csv)")
    parser.add_argument("--batch-size", type=int, default=50, help="Transaction batch commit size (default: 50)")

    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f"Error: Dataset file not found at '{args.file_path}'")
        sys.exit(1)

    print("==================================================")
    print("CODING ARENA PROBLEM IMPORT PIPELINE")
    print("==================================================")
    print(f"Dataset path: {args.file_path}")
    print(f"Batch size: {args.batch_size}")
    print("Connecting to PostgreSQL...")

    importer = ProblemImporter(batch_size=args.batch_size)

    async with AsyncSessionLocal() as session:
        report = await importer.import_from_file(session, args.file_path)

    print("\n---------------- IMPORT REPORT -------------------")
    print(f"Total Records: {report.total_records}")
    print(f"Successfully Imported: {report.imported}")
    print(f"Duplicates Skipped:    {report.duplicates}")
    print(f"Invalid / Validation:  {report.invalid}")
    print(f"Commit Failures:       {report.failed}")
    if report.errors:
        print("\nErrors (sample of first 10):")
        for err in report.errors[:10]:
            print(f" - {err}")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
