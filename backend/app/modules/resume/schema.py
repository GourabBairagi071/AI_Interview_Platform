from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# RESUME RESPONSE
# ============================================================

class ResumeResponse(BaseModel):

    id: UUID
    user_id: UUID
    filename: str
    file_url: str
    uploaded_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# ============================================================
# RESUME UPLOAD
# ============================================================

class ResumeUploadResponse(BaseModel):

    message: str
    resume: ResumeResponse


# ============================================================
# RESUME DELETE
# ============================================================

class ResumeDeleteResponse(BaseModel):

    message: str


# ============================================================
# RESUME ANALYSIS
# ============================================================

class ResumeAnalysisResponse(BaseModel):

    message: str
    resume: ResumeResponse
    analysis: dict


# ============================================================
# AI RESUME OPTIMIZER REQUEST
# ============================================================

class ResumeOptimizeRequest(BaseModel):

    target_role: str = Field(
        min_length=2,
        max_length=100,
    )


# ============================================================
# AI RESUME OPTIMIZER RESPONSE
# ============================================================

class ResumeOptimizeResponse(BaseModel):

    message: str
    resume: ResumeResponse
    optimized_resume: dict