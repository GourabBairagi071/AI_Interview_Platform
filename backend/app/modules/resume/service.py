from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.resume.model import Resume
from app.modules.resume.ai_service import (
    analyze_resume,
    generate_optimized_resume,
)


# ============================================================
# GET USER RESUME
# ============================================================

async def get_user_resume(
    db: AsyncSession,
    user_id,
) -> Resume | None:

    result = await db.execute(
        select(Resume).where(
            Resume.user_id == user_id
        )
    )

    return result.scalar_one_or_none()


# ============================================================
# CREATE OR UPDATE RESUME
# ============================================================

async def create_or_update_resume(
    db: AsyncSession,
    user_id,
    filename: str,
    file_url: str,
) -> Resume:

    result = await db.execute(
        select(Resume).where(
            Resume.user_id == user_id
        )
    )

    resume = result.scalar_one_or_none()

    if resume:

        resume.filename = filename
        resume.file_url = file_url

    else:

        resume = Resume(
            user_id=user_id,
            filename=filename,
            file_url=file_url,
        )

        db.add(resume)

    await db.commit()
    await db.refresh(resume)

    return resume


# ============================================================
# DELETE USER RESUME
# ============================================================

async def delete_user_resume(
    db: AsyncSession,
    user_id,
) -> bool:

    result = await db.execute(
        select(Resume).where(
            Resume.user_id == user_id
        )
    )

    resume = result.scalar_one_or_none()

    if not resume:
        return False

    await db.delete(resume)
    await db.commit()

    return True


# ============================================================
# EXTRACT TEXT FROM RESUME
# ============================================================

def extract_resume_text(
    file_path: Path,
) -> str:

    if not file_path.exists():

        raise ValueError(
            "Resume file not found"
        )

    extension = (
        file_path.suffix.lower()
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if extension == ".pdf":

        try:

            import pypdf

            reader = pypdf.PdfReader(
                str(file_path)
            )

            pages = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pages.append(text)

            return "\n".join(pages).strip()

        except ImportError:

            raise ValueError(
                "pypdf is not installed. "
                "Run: pip install pypdf"
            )

        except Exception as exc:

            raise ValueError(
                f"Could not read PDF resume: {exc}"
            ) from exc


    # --------------------------------------------------------
    # DOCX
    # --------------------------------------------------------

    if extension == ".docx":

        try:

            from docx import Document

            document = Document(
                str(file_path)
            )

            paragraphs = []

            for paragraph in document.paragraphs:

                text = paragraph.text.strip()

                if text:
                    paragraphs.append(text)

            return "\n".join(
                paragraphs
            ).strip()

        except ImportError:

            raise ValueError(
                "python-docx is not installed. "
                "Run: pip install python-docx"
            )

        except Exception as exc:

            raise ValueError(
                f"Could not read DOCX resume: {exc}"
            ) from exc


    raise ValueError(
        "Unsupported resume format. "
        "Only PDF and DOCX are supported."
    )


# ============================================================
# ANALYZE RESUME FILE
# ============================================================

async def analyze_resume_file(
    file_path: Path,
) -> dict:

    resume_text = extract_resume_text(
        file_path
    )

    if not resume_text:

        raise ValueError(
            "Could not extract text from the resume"
        )

    analysis = await analyze_resume(
        resume_text=resume_text
    )

    return {
        "text": resume_text,
        "analysis": analysis,
    }


# ============================================================
# GENERATE OPTIMIZED RESUME
# ============================================================

async def generate_optimized_resume_from_file(
    file_path: Path,
    target_role: str,
) -> dict:

    # --------------------------------------------------------
    # Extract existing resume text
    # --------------------------------------------------------

    resume_text = extract_resume_text(
        file_path
    )

    if not resume_text:

        raise ValueError(
            "Could not extract text from the resume"
        )

    # --------------------------------------------------------
    # Generate optimized resume using AI
    # --------------------------------------------------------

    optimized_resume = (
        await generate_optimized_resume(
            resume_text=resume_text,
            target_role=target_role,
        )
    )

    return optimized_resume