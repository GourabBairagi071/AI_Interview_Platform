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
# ATS PDF GENERATOR (REPORTLAB)
# ============================================================

import base64
import html
import io
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def normalize_ats_text(text: str) -> str:
    """
    Normalizes text for ATS-friendly PDF generation with Helvetica.
    Replaces problematic Unicode characters that cause black box / unmapped glyph
    rendering in standard Type 1 fonts, while preserving legitimate alphanumeric,
    accented characters, dates, hyphens, and punctuation.
    """
    if not text:
        return ""

    s = str(text)

    # 1. Normalize unicode spaces & zero-width characters
    s = (
        s.replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("\u2009", " ")
        .replace("\u2002", " ")
        .replace("\u2003", " ")
    )
    s = (
        s.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )

    # 2. Normalize dashes & hyphens (En-dash, Em-dash, Figure dash, Minus sign, etc.) to standard ASCII hyphen
    s = (
        s.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2015", "-")
        .replace("\u2212", "-")
        .replace("\u2012", "-")
    )

    # 3. Normalize curly quotes and apostrophes to standard ASCII quotes
    s = (
        s.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201a", "'")
        .replace("\u201b", "'")
        .replace("`", "'")
    )
    s = (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u201e", '"')
        .replace("\u201f", '"')
        .replace("\u00ab", '"')
        .replace("\u00bb", '"')
    )

    # 4. Strip decorative bullet glyphs, squares, stars, checks, and DEL control codes
    s = re.sub(
        r"[\u2022\u25cf\u25aa\u25ab\u25b8\u2043\u2219\u25c6\u25c7\u25a0\u25a1\u2713\u2714\u2605\u2726\x7f]+",
        " ",
        s,
    )

    # 5. Clean up any control characters (except newline/tab)
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", s)

    # 6. Normalize multiple consecutive spaces
    s = re.sub(r" +", " ", s)

    return s.strip()


def clean_bullet_item(item_text: str) -> str:
    """
    Strips any leading bullet or dash marker the AI or source document prepended,
    normalizes the text, and returns a clean sentence ready for bullet formatting.
    """
    t = normalize_ats_text(item_text)
    t = re.sub(r"^[-*•▪▫–—\s]+", "", t).strip()
    return t


def generate_ats_resume_pdf(resume_data: dict) -> bytes:
    """
    Generate an ATS-friendly, clean single-column PDF resume without black marks.

    Adheres strictly to ATS guidelines:
    - Standard Letter size, 0.5 inch (36pt) margins
    - Standard fonts (Helvetica, Helvetica-Bold)
    - Fully selectable text
    - Standard safe text bullets (- item) to eliminate \\x7f black boxes
    - Standard ASCII pipe delimiter ( | ) for contact info and sub-meta
    - Single-column ATS structure:
      NAME
      Contact Information
      PROFESSIONAL SUMMARY
      SKILLS
      WORK EXPERIENCE
      PROJECTS
      EDUCATION
      CERTIFICATIONS
      ACHIEVEMENTS
    - Only includes sections for which source information actually exists.
    - Automatic page flow for multiple pages without text cutoff or overlap.
    """
    def _escape(val) -> str:
        if val is None:
            return ""
        cleaned = normalize_ats_text(str(val))
        return html.escape(cleaned)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    name_style = ParagraphStyle(
        "ATSName",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Centered
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2,
    )

    contact_style = ParagraphStyle(
        "ATSContact",
        parent=normal,
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,  # Centered
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "ATSHeading",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=2,
        textColor=colors.HexColor("#0f172a"),
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ATSBody",
        parent=normal,
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ATSBullet",
        parent=normal,
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=2,
        textColor=colors.HexColor("#1e293b"),
    )

    sub_left = ParagraphStyle(
        "ATSSubLeft",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#0f172a"),
    )

    sub_right = ParagraphStyle(
        "ATSSubRight",
        parent=normal,
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        alignment=2,  # Right-aligned
        textColor=colors.HexColor("#475569"),
    )

    meta_left = ParagraphStyle(
        "ATSMetaLeft",
        parent=normal,
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # 1. NAME
    candidate_name = _escape(resume_data.get("name") or "Candidate")
    story.append(Paragraph(candidate_name, name_style))

    # 2. CONTACT INFORMATION (joined with clean ASCII pipe separator)
    raw_contact = resume_data.get("contact_info")
    contact_parts = []
    if isinstance(raw_contact, dict):
        for key in ["email", "phone", "location", "linkedin", "github", "website"]:
            val = _escape(raw_contact.get(key, ""))
            if val:
                contact_parts.append(val)
    elif isinstance(raw_contact, str) and raw_contact.strip():
        contact_parts.append(_escape(raw_contact))

    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
    else:
        story.append(Spacer(1, 6))

    def _add_section_heading(title: str):
        story.append(Paragraph(f"<b>{title.upper()}</b>", heading_style))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.75,
                color=colors.HexColor("#94a3b8"),
                spaceBefore=2,
                spaceAfter=5,
            )
        )

    # 3. PROFESSIONAL SUMMARY
    summary = _escape(
        resume_data.get("professional_summary")
        or resume_data.get("summary")
        or ""
    )
    if summary:
        _add_section_heading("Professional Summary")
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 4))

    # 4. SKILLS
    skills = resume_data.get("skills", [])
    if isinstance(skills, list) and skills:
        cleaned_skills = [_escape(s) for s in skills if str(s).strip()]
        if cleaned_skills:
            _add_section_heading("Skills")
            story.append(Paragraph(", ".join(cleaned_skills), body_style))
            story.append(Spacer(1, 4))

    # 5. WORK EXPERIENCE
    experience = resume_data.get("experience", [])
    if isinstance(experience, list) and experience:
        valid_exp = []
        for exp in experience:
            if isinstance(exp, dict) and (exp.get("role") or exp.get("company") or exp.get("bullets")):
                valid_exp.append(exp)

        if valid_exp:
            _add_section_heading("Work Experience")
            for idx, item in enumerate(valid_exp):
                role = _escape(item.get("role", ""))
                duration = _escape(item.get("duration", ""))
                company = _escape(item.get("company", ""))
                location = _escape(item.get("location", ""))

                row1 = [
                    Paragraph(f"<b>{role}</b>" if role else "", sub_left),
                    Paragraph(duration, sub_right),
                ]
                t1 = Table([row1], colWidths=[380, 160])
                t1.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ])
                )
                story.append(t1)

                if company or location:
                    row2 = [
                        Paragraph(f"<i>{company}</i>" if company else "", meta_left),
                        Paragraph(location, sub_right),
                    ]
                    t2 = Table([row2], colWidths=[380, 160])
                    t2.setStyle(
                        TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ])
                    )
                    story.append(t2)

                bullets = item.get("bullets", [])
                if isinstance(bullets, list):
                    for bullet in bullets:
                        b_clean = clean_bullet_item(bullet)
                        if b_clean:
                            story.append(
                                Paragraph(f"- {html.escape(b_clean)}", bullet_style)
                            )

                if idx < len(valid_exp) - 1:
                    story.append(Spacer(1, 4))
            story.append(Spacer(1, 4))

    # 6. PROJECTS
    projects = resume_data.get("projects", [])
    if isinstance(projects, list) and projects:
        valid_projects = [p for p in projects if isinstance(p, dict) and p.get("name")]
        if valid_projects:
            _add_section_heading("Projects")
            for idx, proj in enumerate(valid_projects):
                proj_name = _escape(proj.get("name", ""))
                techs = proj.get("technologies", [])
                tech_str = ""
                if isinstance(techs, list) and techs:
                    tech_str = ", ".join([_escape(t) for t in techs if str(t).strip()])

                proj_line = f"<b>{proj_name}</b>"
                if tech_str:
                    proj_line += f" | <i>Technologies: {tech_str}</i>"

                story.append(Paragraph(proj_line, sub_left))

                bullets = proj.get("bullets", [])
                if isinstance(bullets, list):
                    for bullet in bullets:
                        b_clean = clean_bullet_item(bullet)
                        if b_clean:
                            story.append(
                                Paragraph(f"- {html.escape(b_clean)}", bullet_style)
                            )

                if idx < len(valid_projects) - 1:
                    story.append(Spacer(1, 4))
            story.append(Spacer(1, 4))

    # 7. EDUCATION
    education = resume_data.get("education", [])
    if isinstance(education, list) and education:
        valid_edu = [e for e in education if isinstance(e, dict) and (e.get("degree") or e.get("institution"))]
        if valid_edu:
            _add_section_heading("Education")
            for idx, edu in enumerate(valid_edu):
                degree = _escape(edu.get("degree", ""))
                duration = _escape(edu.get("duration", ""))
                institution = _escape(edu.get("institution", ""))
                grade = _escape(edu.get("grade", ""))

                row = [
                    Paragraph(f"<b>{degree}</b>" if degree else "", sub_left),
                    Paragraph(duration, sub_right),
                ]
                t = Table([row], colWidths=[380, 160])
                t.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ])
                )
                story.append(t)

                if institution or grade:
                    inst_line = f"<i>{institution}</i>" if institution else ""
                    if grade:
                        inst_line += f" | GPA/Score: {grade}" if inst_line else f"GPA/Score: {grade}"
                    story.append(Paragraph(inst_line, meta_left))

                if idx < len(valid_edu) - 1:
                    story.append(Spacer(1, 3))
            story.append(Spacer(1, 4))

    # 8. CERTIFICATIONS
    certifications = resume_data.get("certifications", [])
    if isinstance(certifications, list) and certifications:
        cleaned_certs = [clean_bullet_item(c) for c in certifications if str(c).strip()]
        if cleaned_certs:
            _add_section_heading("Certifications")
            for cert in cleaned_certs:
                if cert:
                    story.append(Paragraph(f"- {html.escape(cert)}", bullet_style))
            story.append(Spacer(1, 4))

    # 9. ACHIEVEMENTS
    achievements = resume_data.get("achievements", [])
    if isinstance(achievements, list) and achievements:
        cleaned_ach = [clean_bullet_item(a) for a in achievements if str(a).strip()]
        if cleaned_ach:
            _add_section_heading("Achievements")
            for ach in cleaned_ach:
                if ach:
                    story.append(Paragraph(f"- {html.escape(ach)}", bullet_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()


# ============================================================
# GENERATE OPTIMIZED RESUME FROM FILE
# ============================================================

async def generate_optimized_resume_from_file(
    file_path: Path,
    target_role: str,
    user_name: str | None = None,
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

    # Use authenticated user's name if extracted name is empty/placeholder
    if (
        not optimized_resume.get("name")
        or "candidate" in str(optimized_resume.get("name", "")).lower()
    ) and user_name:
        optimized_resume["name"] = user_name

    # --------------------------------------------------------
    # Generate ATS PDF
    # --------------------------------------------------------
    pdf_bytes = generate_ats_resume_pdf(
        resume_data=optimized_resume
    )

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    return {
        "optimized_resume": optimized_resume,
        "pdf_bytes": pdf_bytes,
        "pdf_base64": pdf_base64,
    }