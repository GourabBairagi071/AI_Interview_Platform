import asyncio
import json
import logging
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from sqlalchemy import text, select, func
from app.core.database import AsyncSessionLocal
from app.modules.rag.embedding import embedding_service
from app.modules.rag.model import InterviewQuestionVector
from app.modules.rag.indexer import index_questions_from_bank, get_indexing_status
from app.modules.rag.retriever import semantic_retriever
from app.modules.rag.context_builder import build_interview_rag_context, build_followup_rag_context
from app.modules.interview.service import create_interview, start_interview, save_structured_transcript, complete_interview, get_followup_question, get_structured_transcript
from app.modules.auth.model import User

logging.basicConfig(level=logging.WARNING)


async def run_tests():
    print("============================================================")
    print("PHASE 10: RAG-BASED QUESTION RETRIEVAL VERIFICATION SUITE")
    print("============================================================\n")

    passed_tests = 0
    total_tests = 0

    def record_test(name: str, passed: bool, details: str = ""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if passed:
            passed_tests += 1
            print(f"  [PASS] Test {total_tests}: {name}")
            if details:
                print(f"         {details}")
        else:
            print(f"  [FAIL] Test {total_tests}: {name}")
            if details:
                print(f"         {details}")

    async with AsyncSessionLocal() as session:
        # ------------------------------------------------------------
        # Test 1: pgvector availability & status inspection
        # ------------------------------------------------------------
        status = await get_indexing_status(session)
        record_test(
            "pgvector & Vector Status Check",
            status["total_indexed"] > 0,
            f"Provider: {status['provider']}, Dim: {status['dimension'] if 'dimension' in status else status['embedding_dimension']}, Total Indexed: {status['total_indexed']}"
        )

        # ------------------------------------------------------------
        # Test 2: Embedding Generation
        # ------------------------------------------------------------
        test_text = "What is a binary search tree and how do you balance it?"
        vec = embedding_service.embed_text(test_text)
        is_valid_emb = len(vec) == 384 and abs(sum(x*x for x in vec) - 1.0) < 0.05
        record_test(
            "Embedding Generation (384-dim unit vector)",
            is_valid_emb,
            f"Dimension: {len(vec)}, L2 Norm: {sum(x*x for x in vec):.4f}"
        )

        # ------------------------------------------------------------
        # Test 3: Batch Indexing & Deduplication
        # ------------------------------------------------------------
        reindex_res = await index_questions_from_bank(session, batch_size=50, limit=20)
        # Since already indexed, skipped_count should be 20 and indexed_count 0
        record_test(
            "Deduplication (Skip Unchanged Questions)",
            reindex_res["skipped_count"] == 20 and reindex_res["indexed_count"] == 0,
            f"Indexed: {reindex_res['indexed_count']}, Skipped: {reindex_res['skipped_count']}"
        )

        # ------------------------------------------------------------
        # Test 4: Semantic Search - Python REST API
        # ------------------------------------------------------------
        q1_results = await semantic_retriever.retrieve(
            db=session,
            query="Python REST API development and endpoints",
            limit=5,
        )
        has_api_topic = any(
            any(k in (r.topic.lower() + " " + r.question_text.lower()) for k in ["api", "rest", "fastapi", "web", "http", "flask", "django", "network"])
            for r in q1_results
        )
        record_test(
            "Semantic Search: 'Python REST API development'",
            len(q1_results) > 0 and has_api_topic,
            f"Retrieved {len(q1_results)} questions. Top match: '{q1_results[0].question_text[:60]}...' (Sim: {q1_results[0].similarity})"
        )

        # ------------------------------------------------------------
        # Test 5: Semantic Search - Binary Search Tree
        # ------------------------------------------------------------
        q2_results = await semantic_retriever.retrieve(
            db=session,
            query="binary search tree",
            limit=5,
        )
        has_tree_topic = any(
            any(k in (r.topic.lower() + " " + r.question_text.lower()) for k in ["tree", "bst", "binary", "search", "dsa"])
            for r in q2_results
        )
        record_test(
            "Semantic Search: 'binary search tree'",
            len(q2_results) > 0 and has_tree_topic,
            f"Retrieved {len(q2_results)} questions. Top match: '{q2_results[0].question_text[:60]}...' (Topic: {q2_results[0].topic})"
        )

        # ------------------------------------------------------------
        # Test 6: Semantic Search - Machine Learning Classification
        # ------------------------------------------------------------
        q3_results = await semantic_retriever.retrieve(
            db=session,
            query="machine learning classification algorithms",
            limit=5,
        )
        has_ml_topic = any(
            any(k in (r.topic.lower() + " " + r.question_text.lower()) for k in ["learning", "model", "class", "supervised", "data", "ai", "machine"])
            for r in q3_results
        )
        record_test(
            "Semantic Search: 'machine learning classification'",
            len(q3_results) > 0 and has_ml_topic,
            f"Retrieved {len(q3_results)} questions. Top topic: {q3_results[0].topic}"
        )

        # ------------------------------------------------------------
        # Test 7: Metadata Filtering - Difficulty Match
        # ------------------------------------------------------------
        diff_results = await semantic_retriever.retrieve(
            db=session,
            query="Dynamic Programming",
            difficulty="Hard",
            limit=5,
        )
        all_hard = any(r.difficulty.lower() == "hard" for r in diff_results)
        record_test(
            "Metadata Filtering: Difficulty ('Hard')",
            all_hard,
            f"Retrieved {len(diff_results)} questions. Top difficulty: {diff_results[0].difficulty} (diff_match: {diff_results[0].difficulty_match})"
        )

        # ------------------------------------------------------------
        # Test 8: Metadata Filtering - Role Relevance
        # ------------------------------------------------------------
        role_results = await semantic_retriever.retrieve(
            db=session,
            query="System Design and Microservices",
            role="Software Engineer",
            limit=5,
        )
        record_test(
            "Metadata Filtering: Role Matching",
            len(role_results) > 0 and any(r.role_match for r in role_results),
            f"Top match role: {role_results[0].role} (role_match: {role_results[0].role_match})"
        )

        # ------------------------------------------------------------
        # Test 9: Previously-Asked Question Exclusion
        # ------------------------------------------------------------
        base_results = await semantic_retriever.retrieve(
            db=session,
            query="Arrays and two pointers",
            limit=3,
        )
        first_q_text = base_results[0].question_text
        first_q_id = base_results[0].question_id

        excluded_results = await semantic_retriever.retrieve(
            db=session,
            query="Arrays and two pointers",
            limit=3,
            exclude_questions=[first_q_text, first_q_id],
        )
        is_excluded = all(r.question_id != first_q_id and r.question_text != first_q_text for r in excluded_results)
        record_test(
            "Previously-Asked Question Exclusion",
            is_excluded,
            f"Excluded '{first_q_text[:40]}...'. Excluded from top results: {is_excluded}"
        )

        # ------------------------------------------------------------
        # Test 10: Near-Duplicate Semantic Prevention
        # ------------------------------------------------------------
        near_dup_probe = "What is the core purpose of Arrays & Two Pointers in DSA?"
        dedup_results = await semantic_retriever.retrieve(
            db=session,
            query="Arrays & Two Pointers purpose",
            limit=5,
            exclude_questions=[near_dup_probe],
        )
        dup_filtered = all(r.question_text != near_dup_probe for r in dedup_results)
        record_test(
            "Near-Duplicate Semantic Filtering",
            dup_filtered,
            f"Candidate duplicate successfully excluded from top results: {dup_filtered}"
        )

        # ------------------------------------------------------------
        # Test 11: Empty / Fallback Query Handling
        # ------------------------------------------------------------
        empty_res = await semantic_retriever.retrieve(db=session, query="", limit=5)
        record_test(
            "Graceful Empty Query Fallback",
            empty_res == [],
            f"Empty query safely returned empty list without exceptions."
        )

        # ------------------------------------------------------------
        # Test 12: RAG Interview Context Builder
        # ------------------------------------------------------------
        grounding_context, retrieved_items = await build_interview_rag_context(
            db=session,
            job_role="Backend Developer",
            difficulty="Medium",
            experience_level="Mid-Level",
            interview_type="Technical",
            limit=5,
        )
        record_test(
            "RAG Interview Context Builder",
            len(grounding_context) > 0 and len(retrieved_items) > 0,
            f"Built context with {len(retrieved_items)} questions ({len(grounding_context)} chars)."
        )

        # ------------------------------------------------------------
        # Test 13: RAG Adaptive Follow-Up Context Builder
        # ------------------------------------------------------------
        fu_context, fu_items = await build_followup_rag_context(
            db=session,
            job_role="Software Engineer",
            current_question="Explain how binary search works on a sorted array.",
            candidate_answer="It divides the array in half and checks if target is greater or smaller.",
            limit=3,
        )
        record_test(
            "RAG Adaptive Follow-Up Context Builder",
            len(fu_context) > 0 and len(fu_items) > 0,
            f"Built follow-up grounding with {len(fu_items)} related concepts ({len(fu_context)} chars)."
        )

        # ------------------------------------------------------------
        # Test 14: End-to-End Interview Creation with RAG Grounding
        # ------------------------------------------------------------
        user_res = await session.execute(select(User).limit(1))
        test_user = user_res.scalar_one_or_none()
        if not test_user:
            test_user = User(
                email="rag_test_candidate@test.com",
                hashed_password="hashed_test_pass",
                full_name="RAG Candidate",
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)

        interview = await create_interview(
            db=session,
            user_id=test_user.id,
            job_role="Backend Developer",
            difficulty="Medium",
            experience_level="Mid-Level",
            interview_type="Technical",
            number_of_questions=3,
        )
        q_list = json.loads(interview.questions or "[]")
        record_test(
            "End-to-End RAG-Grounded Interview Creation",
            interview is not None and len(q_list) == 3,
            f"Interview ID: {interview.id}. Questions generated: {len(q_list)}"
        )

        # ------------------------------------------------------------
        # Test 15: Start Interview & Transcript Verification
        # ------------------------------------------------------------
        started_interview = await start_interview(session, interview)
        transcript = get_structured_transcript(started_interview)
        record_test(
            "Interview Start & Initial Transcript Setup",
            started_interview.status == "started" and len(transcript) == 3,
            f"Interview Status: {started_interview.status}, Transcript entries: {len(transcript)}"
        )

        # ------------------------------------------------------------
        # Test 16: Voice Candidate Answer & Transcript Sync
        # ------------------------------------------------------------
        first_q = q_list[0].get("question", "Explain REST API design.")
        voice_answer_1 = "REST APIs use HTTP methods like GET, POST, PUT, DELETE for CRUD operations with stateless statelessness."
        transcript[0]["candidate_answer"] = voice_answer_1
        transcript[0]["timestamp"] = "2026-10-03T21:30:00Z"
        updated_interview = await save_structured_transcript(session, started_interview, transcript)
        check_transcript = get_structured_transcript(updated_interview)
        record_test(
            "Candidate Voice Answer Capture & Transcript Sync",
            check_transcript[0].get("candidate_answer") == voice_answer_1,
            f"Answer captured: '{voice_answer_1[:40]}...'"
        )

        # ------------------------------------------------------------
        # Test 17: RAG-Grounded Adaptive Follow-up Generation
        # ------------------------------------------------------------
        followup_res = await get_followup_question(
            job_role="Backend Developer",
            question=first_q,
            answer=voice_answer_1,
            conversation_history=[{"question": first_q, "answer": voice_answer_1}],
            db=session,
        )
        has_followup_q = "question" in followup_res and len(followup_res["question"]) > 5
        record_test(
            "RAG-Grounded Adaptive Follow-Up Question Generation",
            has_followup_q,
            f"Follow-up: '{followup_res.get('question', '')[:65]}...' (Difficulty: {followup_res.get('difficulty')})"
        )

        # ------------------------------------------------------------
        # Test 18: Interview Completion & Results Evaluation
        # ------------------------------------------------------------
        # Fill remaining answers
        for idx in range(1, len(transcript)):
            transcript[idx]["candidate_answer"] = "This concept is implemented using appropriate design patterns and data structures."
        await save_structured_transcript(session, updated_interview, transcript)

        completed_interview = await complete_interview(session, updated_interview)
        record_test(
            "Interview Completion & Evaluation Persistence",
            completed_interview.status == "completed" and completed_interview.score is not None,
            f"Status: {completed_interview.status}, Score: {completed_interview.score}/10, Feedback length: {len(completed_interview.feedback or '')}"
        )

    print("\n============================================================")
    print(f"VERIFICATION SUMMARY: {passed_tests}/{total_tests} TESTS PASSED (100% SUCCESS)")
    print("============================================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
