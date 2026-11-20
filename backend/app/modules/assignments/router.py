import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.admin.permissions import require_permission
from app.modules.assignments.schema import (
    AdminAssignmentDetailResponse,
    AssignmentAnalyticsResponse,
    CandidateAssignmentItem,
    CreateAssignmentRequest,
    SubmitAssignmentRequest,
    UpdateAssignmentStatusRequest,
)
from app.modules.assignments.service import AssignmentService
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

admin_assignment_router = APIRouter(prefix="/admin/assignments", tags=["Admin Assignments"])
candidate_assignment_router = APIRouter(prefix="/candidate/assignments", tags=["Candidate Assignments"])


# ============================================================
# ADMIN ASSIGNMENT MANAGEMENT ENDPOINTS
# ============================================================

@admin_assignment_router.get(
    "",
    summary="List assignments with progress metrics",
)
async def list_assignments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    assignment_type: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    return await AssignmentService.list_admin_assignments(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        assignment_type=assignment_type,
        search=search,
    )


@admin_assignment_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create and dispatch assignment to target candidates",
)
async def create_assignment(
    data: CreateAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    assignment = await AssignmentService.create_assignment(
        db=db,
        data=data,
        actor=current_user,
    )
    return {
        "id": str(assignment.id),
        "title": assignment.title,
        "status": assignment.status,
        "assignment_type": assignment.assignment_type,
        "priority": assignment.priority,
        "due_date": assignment.due_date,
        "created_at": assignment.created_at,
    }


@admin_assignment_router.get(
    "/analytics",
    response_model=AssignmentAnalyticsResponse,
    summary="Global assignment completion and dispatch metrics",
)
async def get_assignment_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("analytics.view")),
):
    return await AssignmentService.get_assignment_analytics(db)


@admin_assignment_router.get(
    "/{assignment_id}",
    response_model=AdminAssignmentDetailResponse,
    summary="Get assignment details and recipient candidates",
)
async def get_assignment_detail(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    detail = await AssignmentService.get_admin_assignment_detail(db, assignment_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return detail


@admin_assignment_router.put(
    "/{assignment_id}/status",
    summary="Update assignment status (CANCEL, ARCHIVE, PUBLISH)",
)
async def update_assignment_status(
    assignment_id: uuid.UUID,
    data: UpdateAssignmentStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
):
    success = await AssignmentService.update_assignment_status(
        db=db,
        assignment_id=assignment_id,
        new_status=data.status,
        actor=current_user,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"message": "Status updated successfully", "status": data.status}


# ============================================================
# CANDIDATE ASSIGNED TASKS ENDPOINTS (Zero IDOR)
# ============================================================

@candidate_assignment_router.get(
    "",
    response_model=list[CandidateAssignmentItem],
    summary="List tasks assigned to current authenticated candidate",
)
async def get_my_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AssignmentService.get_candidate_assigned_tasks(
        db=db,
        candidate_id=current_user.id,
    )


@candidate_assignment_router.post(
    "/{assignment_id}/start",
    summary="Start or launch an assigned task",
)
async def start_assigned_task(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await AssignmentService.start_candidate_assignment(
        db=db,
        assignment_id=assignment_id,
        candidate_id=current_user.id,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Assigned task not found for this candidate")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@candidate_assignment_router.post(
    "/{assignment_id}/submit",
    summary="Submit completion of an assigned task",
)
async def submit_assigned_task(
    assignment_id: uuid.UUID,
    data: SubmitAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await AssignmentService.submit_candidate_assignment(
        db=db,
        assignment_id=assignment_id,
        candidate_id=current_user.id,
        data=data,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Assigned task not found for this candidate")
    return res
