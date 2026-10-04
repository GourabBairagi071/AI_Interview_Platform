from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.rag.indexer import get_indexing_status, index_questions_from_bank
from app.modules.rag.retriever import semantic_retriever
from app.modules.rag.schema import (
    RAGIndexRequest,
    RAGIndexResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGStatusResponse,
)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.get(
    "/status",
    response_model=RAGStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_rag_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns current vector indexing status, embedding provider, dimension, and total indexed questions.
    """
    status_data = await get_indexing_status(db)
    return status_data


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_rag_questions(
    payload: RAGSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Performs semantic and hybrid metadata retrieval against indexed interview questions.
    """
    results = await semantic_retriever.retrieve(
        db=db,
        query=payload.query,
        role=payload.role,
        difficulty=payload.difficulty,
        topic=payload.topic,
        skills=payload.skills,
        question_type=payload.question_type,
        company=payload.company,
        limit=payload.limit,
        exclude_questions=payload.exclude_questions,
    )

    return {
        "query": payload.query,
        "total_retrieved": len(results),
        "results": results,
    }


@router.post(
    "/index",
    response_model=RAGIndexResponse,
    status_code=status.HTTP_200_OK,
)
async def index_rag_questions(
    payload: RAGIndexRequest = RAGIndexRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Administrative endpoint to index practice questions into the vector store.
    """
    result = await index_questions_from_bank(
        db=db,
        batch_size=payload.batch_size,
        limit=payload.limit,
        force_reindex=payload.force_reindex,
    )

    return {
        "status": "success",
        "indexed_count": result["indexed_count"],
        "skipped_count": result["skipped_count"],
        "total_vectors": result["total_vectors"],
    }


@router.post(
    "/reindex",
    response_model=RAGIndexResponse,
    status_code=status.HTTP_200_OK,
)
async def reindex_rag_questions(
    payload: RAGIndexRequest = RAGIndexRequest(force_reindex=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Administrative endpoint to force full reindexing of the vector store.
    """
    result = await index_questions_from_bank(
        db=db,
        batch_size=payload.batch_size,
        limit=payload.limit,
        force_reindex=True,
    )

    return {
        "status": "success",
        "indexed_count": result["indexed_count"],
        "skipped_count": result["skipped_count"],
        "total_vectors": result["total_vectors"],
    }
