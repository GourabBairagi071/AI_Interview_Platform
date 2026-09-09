from pathlib import Path
import shutil

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User

from app.modules.resume.schema import (
    ResumeAnalysisResponse,
    ResumeDeleteResponse,
    ResumeOptimizeRequest,
    ResumeOptimizeResponse,
    ResumeResponse,
    ResumeUploadResponse,
)

from app.modules.resume.service import (
    analyze_resume_file,
    create_or_update_resume,
    delete_user_resume,
    generate_optimized_resume_from_file,
    get_user_resume,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/resume",
    tags=["Resume"],
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

UPLOAD_DIR = Path("uploads/resumes")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


# ============================================================
# GET CURRENT USER RESUME
# GET /api/v1/resume
# ============================================================

@router.get(
    "",
    response_model=ResumeResponse,
)
async def get_resume(
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    resume = await get_user_resume(
        db=db,
        user_id=current_user.id,
    )

    if not resume:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return resume


# ============================================================
# UPLOAD RESUME
# POST /api/v1/resume
# ============================================================

@router.post(
    "",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only PDF and DOCX files are allowed"
            ),
        )

    # --------------------------------------------------------
    # Remove previous resume file
    # --------------------------------------------------------

    old_resume = await get_user_resume(
        db=db,
        user_id=current_user.id,
    )

    if old_resume:

        old_file = Path(
            old_resume.file_url.lstrip("/")
        )

        if old_file.exists():

            try:
                old_file.unlink()
            except OSError:
                pass

    # --------------------------------------------------------
    # Generate safe filename
    # --------------------------------------------------------

    safe_filename = (
        f"{current_user.id}{extension}"
    )

    file_path = (
        UPLOAD_DIR / safe_filename
    )

    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------

    try:

        with file_path.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to save resume: {exc}"
            ),
        ) from exc

    # --------------------------------------------------------
    # File URL
    # --------------------------------------------------------

    file_url = (
        f"/uploads/resumes/{safe_filename}"
    )

    # --------------------------------------------------------
    # Save database record
    # --------------------------------------------------------

    try:

        resume = await create_or_update_resume(
            db=db,
            user_id=current_user.id,
            filename=file.filename,
            file_url=file_url,
        )

    except Exception as exc:

        # Remove physical file if DB operation fails

        if file_path.exists():

            try:
                file_path.unlink()
            except OSError:
                pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to save resume information: {exc}"
            ),
        ) from exc

    return {
        "message": "Resume uploaded successfully",
        "resume": resume,
    }


# ============================================================
# ANALYZE CURRENT RESUME
# POST /api/v1/resume/analyze
# ============================================================

@router.post(
    "/analyze",
    response_model=ResumeAnalysisResponse,
)
async def analyze_current_resume(
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    # --------------------------------------------------------
    # Find resume
    # --------------------------------------------------------

    resume = await get_user_resume(
        db=db,
        user_id=current_user.id,
    )

    if not resume:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please upload a resume first",
        )

    # --------------------------------------------------------
    # Find physical file
    # --------------------------------------------------------

    file_path = Path(
        resume.file_url.lstrip("/")
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found",
        )

    # --------------------------------------------------------
    # Analyze using AI
    # --------------------------------------------------------

    try:

        result = await analyze_resume_file(
            file_path=file_path
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Resume analysis failed: {exc}"
            ),
        ) from exc

    # --------------------------------------------------------
    # Return analysis
    # --------------------------------------------------------

    return {
        "message": "Resume analyzed successfully",
        "resume": resume,
        "analysis": result["analysis"],
    }


# ============================================================
# GENERATE ATS OPTIMIZED RESUME
# POST /api/v1/resume/optimize
# ============================================================

@router.post(
    "/optimize",
    response_model=ResumeOptimizeResponse,
)
async def optimize_current_resume(
    data: ResumeOptimizeRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    # --------------------------------------------------------
    # Find user's resume
    # --------------------------------------------------------

    resume = await get_user_resume(
        db=db,
        user_id=current_user.id,
    )

    if not resume:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please upload a resume first",
        )

    # --------------------------------------------------------
    # Check physical file
    # --------------------------------------------------------

    file_path = Path(
        resume.file_url.lstrip("/")
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found",
        )

    # --------------------------------------------------------
    # Validate target role
    # --------------------------------------------------------

    target_role = data.target_role.strip()

    if not target_role:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target job role is required",
        )

    # --------------------------------------------------------
    # Generate optimized resume
    # --------------------------------------------------------

    try:

        optimized_resume = (
            await generate_optimized_resume_from_file(
                file_path=file_path,
                target_role=target_role,
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Resume optimization failed: "
                f"{exc}"
            ),
        ) from exc

    # --------------------------------------------------------
    # Return optimized resume
    # --------------------------------------------------------

    return {
        "message": "Resume optimized successfully",
        "resume": resume,
        "optimized_resume": optimized_resume,
    }


# ============================================================
# DELETE RESUME
# DELETE /api/v1/resume
# ============================================================

@router.delete(
    "",
    response_model=ResumeDeleteResponse,
)
async def delete_resume(
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    # --------------------------------------------------------
    # Find resume
    # --------------------------------------------------------

    resume = await get_user_resume(
        db=db,
        user_id=current_user.id,
    )

    if not resume:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # --------------------------------------------------------
    # Delete physical file
    # --------------------------------------------------------

    file_path = Path(
        resume.file_url.lstrip("/")
    )

    if file_path.exists():

        try:
            file_path.unlink()
        except OSError:
            pass

    # --------------------------------------------------------
    # Delete database record
    # --------------------------------------------------------

    await delete_user_resume(
        db=db,
        user_id=current_user.id,
    )

    return {
        "message": "Resume deleted successfully",
    }