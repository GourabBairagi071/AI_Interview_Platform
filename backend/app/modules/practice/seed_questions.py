"""
Seed canonical question bank and preserve existing interview questions into practice_questions table.
"""
import asyncio
import hashlib
import json
import os
import sys

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.database import AsyncSessionLocal
from app.modules.interview.model import Interview
from app.modules.practice.model import PracticeQuestion
from app.modules.practice.synthesize_canonical_bank import generate_canonical_catalog, slugify, generate_qid

TECH_KEYWORDS = {
    "python": "Python",
    "react": "React",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "c#": "C++",
    "sql": "SQL",
    "database": "DBMS",
    "dbms": "DBMS",
    "postgres": "PostgreSQL",
    "mongo": "MongoDB",
    "node": "Node.js",
    "express": "Express",
    "next": "Next.js",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "cloud": "Cloud",
    "devops": "DevOps",
    "linux": "Linux",
    "git": "Git",
    "system design": "System Design",
    "distributed": "Distributed Systems",
    "security": "Cybersecurity",
    "cyber": "Cybersecurity",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "vision": "Computer Vision",
    "ai": "AI",
    "genai": "GenAI",
    "llm": "LLMs",
    "rag": "RAG",
    "vector": "Vector Databases",
    "langchain": "LangChain",
    "spark": "Spark",
    "kafka": "Kafka",
    "data engineering": "Data Engineering",
    "algorithm": "Algorithms",
    "dsa": "DSA",
    "oop": "OOP",
}

def map_interview_to_technology(q_text: str, job_role: str | None, topic: str | None) -> tuple[str, str]:
    text_to_search = f"{q_text} {job_role or ''} {topic or ''}".lower()
    for kw, tech in TECH_KEYWORDS.items():
        if kw in text_to_search:
            return tech, (topic if topic and len(topic) > 2 else "Interview Essentials")
    return "System Design", (topic if topic and len(topic) > 2 else "General Technical")

async def seed_all_questions():
    print("=" * 60)
    print("SEEDING 5,000+ QUESTION BANK INTO POSTGRESQL")
    print("=" * 60)

    # 1. Generate canonical catalog (5,640 questions)
    canonical_list, dupes, invalid = generate_canonical_catalog()
    catalog_map = {q["id"]: q for q in canonical_list}

    # 2. Extract and preserve all real interview questions from PostgreSQL
    async with AsyncSessionLocal() as session:
        stmt = select(
            Interview.questions,
            Interview.question_evaluations,
            Interview.job_role,
            Interview.difficulty,
        )
        res = await session.execute(stmt)
        interviews = res.all()

        interview_q_count = 0
        preserved_count = 0

        for row in interviews:
            q_raw, eval_raw, job_role, diff = row
            if not q_raw:
                continue

            try:
                qs = json.loads(q_raw)
                evals = json.loads(eval_raw) if eval_raw else []
                eval_map = {}
                if isinstance(evals, list):
                    for idx, ev in enumerate(evals, start=1):
                        if isinstance(ev, dict):
                            eval_map[ev.get("question_number", idx)] = ev

                if isinstance(qs, list):
                    for idx, q_item in enumerate(qs, start=1):
                        q_text = ""
                        q_topic = "General"
                        if isinstance(q_item, dict):
                            q_text = str(q_item.get("question", "")).strip()
                            q_topic = str(q_item.get("topic", "General")).strip()
                        elif isinstance(q_item, str):
                            q_text = q_item.strip()

                        if not q_text or len(q_text) < 10:
                            continue

                        interview_q_count += 1
                        qid = generate_qid(q_text)
                        explanation = ""
                        if idx in eval_map and isinstance(eval_map[idx], dict):
                            explanation = str(eval_map[idx].get("feedback", "")).strip()

                        tech_name, clean_topic = map_interview_to_technology(q_text, job_role, q_topic)
                        tech_slug = slugify(tech_name)
                        topic_slug = slugify(clean_topic)

                        norm_diff = "Medium"
                        if diff and str(diff).lower() in ["easy", "hard"]:
                            norm_diff = str(diff).title()

                        if qid not in catalog_map:
                            preserved_count += 1
                            catalog_map[qid] = {
                                "id": qid,
                                "technology": tech_name,
                                "technology_slug": tech_slug,
                                "topic": clean_topic,
                                "topic_slug": topic_slug,
                                "subtopic": "Interview Question",
                                "question": q_text,
                                "difficulty": norm_diff,
                                "question_type": "Technical",
                                "role": job_role or "Software Engineer",
                                "explanation": explanation or "Comprehensive answer explanation from technical interview evaluation.",
                                "source": "interview"
                            }
                        else:
                            # Enrich existing canonical question if explanation is available
                            if explanation and not catalog_map[qid]["explanation"]:
                                catalog_map[qid]["explanation"] = explanation
            except Exception as e:
                continue

        print(f"Processed {interview_q_count} interview questions. Preserved/Added: {preserved_count} unique.")
        print(f"Total unified catalog items: {len(catalog_map)}")

        # 3. Batch insert / upsert into PostgreSQL practice_questions
        all_items = list(catalog_map.values())
        batch_size = 500
        inserted_total = 0

        for i in range(0, len(all_items), batch_size):
            chunk = all_items[i : i + batch_size]
            stmt = insert(PracticeQuestion).values(chunk)
            # On conflict update fields to preserve freshest data
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "technology": stmt.excluded.technology,
                    "technology_slug": stmt.excluded.technology_slug,
                    "topic": stmt.excluded.topic,
                    "topic_slug": stmt.excluded.topic_slug,
                    "subtopic": stmt.excluded.subtopic,
                    "question": stmt.excluded.question,
                    "difficulty": stmt.excluded.difficulty,
                    "question_type": stmt.excluded.question_type,
                    "role": stmt.excluded.role,
                    "explanation": stmt.excluded.explanation,
                    "source": stmt.excluded.source,
                }
            )
            await session.execute(do_update_stmt)
            await session.commit()
            inserted_total += len(chunk)

        print(f"Successfully upserted {inserted_total} records into practice_questions table.")

        # 4. Query PostgreSQL directly to gather real validated database statistics
        count_stmt = select(func.count(PracticeQuestion.id))
        total_in_db = (await session.execute(count_stmt)).scalar() or 0

        unique_stmt = select(func.count(func.distinct(PracticeQuestion.id)))
        unique_in_db = (await session.execute(unique_stmt)).scalar() or 0

        techs_stmt = select(func.count(func.distinct(PracticeQuestion.technology)))
        techs_in_db = (await session.execute(techs_stmt)).scalar() or 0

        topics_stmt = select(func.count(func.distinct(PracticeQuestion.topic)))
        topics_in_db = (await session.execute(topics_stmt)).scalar() or 0

        diff_stmt = select(PracticeQuestion.difficulty, func.count(PracticeQuestion.id)).group_by(PracticeQuestion.difficulty)
        diff_res = (await session.execute(diff_stmt)).all()
        diff_map = {row[0]: row[1] for row in diff_res}

        easy_count = diff_map.get("Easy", 0)
        med_count = diff_map.get("Medium", 0)
        hard_count = diff_map.get("Hard", 0)

        # 5. Save canonical_bank.json to disk for fast startup caching
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canonical_bank.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, indent=2)

        # 6. Print required statistics format
        print("=" * 60)
        print(f"Total questions: {total_in_db}")
        print(f"Unique questions: {unique_in_db}")
        print(f"Technologies: {techs_in_db}")
        print(f"Topics: {topics_in_db}")
        print(f"Easy: {easy_count}")
        print(f"Medium: {med_count}")
        print(f"Hard: {hard_count}")
        print(f"Invalid: {invalid}")
        print(f"Duplicates removed: {dupes}")
        print("=" * 60)

        assert unique_in_db >= 5000, f"FAILED: Unique questions ({unique_in_db}) < 5000"
        print("[SUCCESS] Question bank seeding verified: >= 5,000 unique questions in database.")

if __name__ == "__main__":
    asyncio.run(seed_all_questions())
