import json
import os
import re

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is not configured. "
        "Check backend/.env"
    )


MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b",
)


client = Groq(
    api_key=GROQ_API_KEY
)# ============================================================
# HELPERS
# ============================================================

def _get_message_content(response) -> str:
    """
    Safely extract text from Groq response.
    """

    try:
        content = response.choices[0].message.content
    except Exception:
        return ""

    if content is None:
        return ""

    return str(content).strip()


def _extract_json(content: str) -> dict:
    """
    Extract JSON from AI response.

    Handles:
    - pure JSON
    - ```json ... ```
    - extra text around JSON
    """

    if not content or not content.strip():
        raise ValueError(
            "AI returned an empty response"
        )

    content = content.strip()

    # Remove markdown code fences
    content = re.sub(
        r"^```json\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"^```\s*",
        "",
        content,
    )

    content = re.sub(
        r"\s*```$",
        "",
        content,
    )

    content = content.strip()

    # First attempt: complete response is JSON
    try:
        result = json.loads(content)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Second attempt: locate first JSON object
    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = content[
            start:end + 1
        ]

        try:
            result = json.loads(json_text)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"AI returned invalid JSON: {exc}"
            ) from exc

    raise ValueError(
        "AI returned an invalid response"
    )


def _safe_list(value):
    """
    Always return a list of strings.
    """

    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def _clean_bullet_list(value):
    """
    Clean bullet list items by stripping decorative bullets, leading dashes/markers,
    and trailing whitespaces.
    """
    if not isinstance(value, list):
        return []

    cleaned = []
    for item in value:
        s = str(item).strip()
        s = re.sub(r"^[\s•▪▫●★✓✔–—\-\*\u2022\u25aa\u25ab\u25cf\u2713\u2714\u2013\u2014]+", "", s).strip()
    return cleaned


def _parse_safe_score(val) -> int | None:
    """
    Safely converts numeric or string ATS score (e.g. 78, '78', '78%', '78/100', '78 out of 100')
    into an integer 0-100. Returns None if value is missing/invalid.
    """
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return int(max(0, min(100, round(val))))
    if isinstance(val, str):
        match = re.search(r"(\d+(?:\.\d+)?)", val.strip())
        if match:
            try:
                num = float(match.group(1))
                return int(max(0, min(100, round(num))))
            except ValueError:
                pass
    return None


# ============================================================
# ANALYZE RESUME
# ============================================================

async def analyze_resume(
    resume_text: str,
) -> dict:

    if not resume_text or not resume_text.strip():
        raise ValueError(
            "Resume text is empty"
        )

    # Keep input reasonably small
    MAX_RESUME_CHARS = 7000

    resume_text = resume_text.strip()

    if len(resume_text) > MAX_RESUME_CHARS:
        resume_text = resume_text[:MAX_RESUME_CHARS]

    prompt = f"""
You are an ATS resume analyzer.

Analyze this resume:

{resume_text}

Return ONLY valid JSON.

Required JSON:

{{
  "ats_score": 0,
  "skills": [],
  "strengths": [],
  "weaknesses": [],
  "improvement_suggestions": [],
  "role_matching": [
    {{
      "role": "",
      "match": 0,
      "reason": ""
    }}
  ]
}}

STRICT RULES:

- ats_score: integer 0-100
- skills: maximum 20 items
- strengths: maximum 5 short items
- weaknesses: maximum 5 short items
- improvement_suggestions: maximum 5 short items
- role_matching: maximum 5 roles
- match: integer 0-100
- reason: one short sentence
- Keep every item concise.
- Do not invent information.
- Extract skills only from the resume.
- Return JSON only.
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            temperature=0.1,

            # Increased enough to complete JSON,
            # while keeping request controlled.
            max_completion_tokens=1200,

            response_format={
                "type": "json_object"
            },
        )

    except Exception as exc:

        raise ValueError(
            f"AI resume analysis failed: {exc}"
        ) from exc

    content = _get_message_content(
        response
    )

    result = _extract_json(
        content
    )

    # --------------------------------------------------------
    # ATS SCORE
    # --------------------------------------------------------

    raw_score = (
        result.get("ats_score")
        if result.get("ats_score") is not None
        else result.get("atsScore")
        if result.get("atsScore") is not None
        else result.get("score")
        if result.get("score") is not None
        else result.get("estimated_ats_score")
    )

    parsed_score = _parse_safe_score(raw_score)
    result["ats_score"] = parsed_score if parsed_score is not None else 0


    # --------------------------------------------------------
    # Normalize lists
    # --------------------------------------------------------

    result["skills"] = _safe_list(
        result.get("skills")
    )[:20]

    result["strengths"] = _safe_list(
        result.get("strengths")
    )[:5]

    result["weaknesses"] = _safe_list(
        result.get("weaknesses")
    )[:5]

    result["improvement_suggestions"] = _safe_list(
        result.get("improvement_suggestions", result.get("suggestions"))
    )[:5]

    # --------------------------------------------------------
    # Role matching
    # --------------------------------------------------------

    role_matching = result.get(
        "role_matching",
        [],
    )

    if not isinstance(
        role_matching,
        list,
    ):
        role_matching = []

    clean_roles = []

    for item in role_matching[:5]:

        if not isinstance(
            item,
            dict,
        ):
            continue

        try:

            match = float(
                item.get(
                    "match_percentage",
                    item.get("match", 0),
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            match = 0

        clean_roles.append(
            {
                "role": str(
                    item.get(
                        "role",
                        "",
                    )
                ).strip(),

                "match_percentage": int(
                    max(
                        0,
                        min(
                            100,
                            match,
                        ),
                    )
                ),

                "reason": str(
                    item.get(
                        "reason",
                        "",
                    )
                ).strip(),
            }
        )

    result["role_matching"] = clean_roles

    return result


# ============================================================
# GENERATE ATS OPTIMIZED RESUME
# ============================================================

async def generate_optimized_resume(
    resume_text: str,
    target_role: str,
) -> dict:

    if not resume_text or not resume_text.strip():

        raise ValueError(
            "Resume text is empty"
        )

    if not target_role or not target_role.strip():

        raise ValueError(
            "Target role is required"
        )


    # --------------------------------------------------------
    # Prevent 413 TPM error
    # --------------------------------------------------------

    MAX_RESUME_CHARS = 8000

    resume_text = resume_text.strip()

    if len(resume_text) > MAX_RESUME_CHARS:

        resume_text = resume_text[
            :MAX_RESUME_CHARS
        ]


    target_role = target_role.strip()


    prompt = f"""
You are an expert ATS resume writer and technical recruiter.

TARGET JOB ROLE:
{target_role}

EXISTING RESUME:
----------------
{resume_text}
----------------

Create an ATS-optimized, single-column version of this resume tailored to the target job role.

CRITICAL RULES - STRICT ADHERENCE REQUIRED:

1. ABSOLUTELY NO FABRICATION:
Never invent or hallucinate candidate information.
Never invent:
- company names
- employment history
- job titles
- dates or durations
- degrees or institutions
- CGPA or grades
- certifications
- projects
- achievements or awards
- technologies or tools
- numerical metrics or statistics

2. ONLY SOURCE-BACKED CONTENT:
- Extract the candidate's real name from the resume.
- Extract only contact information actually present in the resume.
- Only include sections and items for which actual source information exists.
- If a section (e.g. certifications, achievements, projects) has no source data in the resume, leave that array empty [].

3. ATS OPTIMIZATION PERMITTED ACTIONS:
- Rewrite phrasing for clarity, conciseness, and professional tone.
- Improve grammar and eliminate repetition.
- Prioritize technical skills and keywords relevant to the target role ({target_role}).
- Reorganize sections into a clean single-column ATS hierarchy.
- Convert responsibilities into strong, truthful bullet points starting with impactful action verbs.
- Optimize keywords naturally based on the target role without keyword-stuffing.

4. ATS-COMPATIBLE TEXT FORMATTING:
- Do NOT use emojis, decorative icons, special bullet glyphs (e.g. •, ▪, ▫, ●, ★, ✔, ✓), or non-standard symbols anywhere in the response.
- In all bullet arrays ("bullets", "certifications", "achievements"), provide plain text strings without leading bullet characters or dashes (e.g. "Spearheaded backend architecture..." NOT "- Spearheaded..." or "• Spearheaded...").
- Use standard ASCII punctuation (hyphens "-" for date ranges, standard single/double quotes, standard ampersand "&").

Return ONLY valid JSON matching this exact structure:

{{
  "name": "Candidate Full Name extracted from resume",
  "contact_info": {{"email": "", "phone": "", "location": "", "linkedin": "", "github": "", "website": ""}},
  "estimated_ats_score": 0,
  "target_role": "{target_role}",
  "professional_summary": "",
  "skills": [],
  "experience": [
    {{
      "company": "",
      "role": "",
      "duration": "",
      "location": "",
      "bullets": []
    }}
  ],
  "projects": [
    {{
      "name": "",
      "technologies": [],
      "bullets": []
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "duration": "",
      "grade": ""
    }}
  ],
  "certifications": [],
  "achievements": [],
  "keywords": [],
  "improvements": [],
  "missing_keywords": []
}}

Return JSON only.
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.15,
            max_completion_tokens=2500,
            response_format={
                "type": "json_object"
            },
        )

    except Exception as exc:

        raise ValueError(
            f"AI resume optimization failed: {exc}"
        ) from exc

    content = _get_message_content(
        response
    )

    result = _extract_json(
        content
    )

    # --------------------------------------------------------
    # ATS SCORE
    # --------------------------------------------------------

    raw_score = (
        result.get("estimated_ats_score")
        if result.get("estimated_ats_score") is not None
        else result.get("ats_score")
        if result.get("ats_score") is not None
        else result.get("score")
    )
    parsed_score = _parse_safe_score(raw_score)
    result["estimated_ats_score"] = parsed_score if parsed_score is not None else 0

    result["target_role"] = target_role

    # --------------------------------------------------------
    # Candidate Name & Contact Info
    # --------------------------------------------------------

    result["name"] = str(result.get("name", "")).strip()

    raw_contact = result.get("contact_info")
    if not isinstance(raw_contact, dict):
        raw_contact = {}

    result["contact_info"] = {
        "email": str(raw_contact.get("email", "")).strip(),
        "phone": str(raw_contact.get("phone", "")).strip(),
        "location": str(raw_contact.get("location", "")).strip(),
        "linkedin": str(raw_contact.get("linkedin", "")).strip(),
        "github": str(raw_contact.get("github", "")).strip(),
        "website": str(raw_contact.get("website", "")).strip(),
    }

    # --------------------------------------------------------
    # Normalize simple lists
    # --------------------------------------------------------

    result["skills"] = _safe_list(result.get("skills"))
    result["certifications"] = _clean_bullet_list(result.get("certifications"))
    result["achievements"] = _clean_bullet_list(result.get("achievements"))
    result["keywords"] = _safe_list(result.get("keywords"))
    result["improvements"] = _safe_list(result.get("improvements"))
    result["missing_keywords"] = _safe_list(result.get("missing_keywords"))

    # --------------------------------------------------------
    # Professional summary
    # --------------------------------------------------------

    result["professional_summary"] = str(
        result.get("professional_summary", result.get("summary", ""))
    ).strip()

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    experience = result.get("experience", [])
    if not isinstance(experience, list):
        experience = []

    clean_experience = []
    for item in experience:
        if not isinstance(item, dict):
            continue

        bullets = _clean_bullet_list(item.get("bullets"))

        clean_experience.append(
            {
                "company": str(item.get("company", "")).strip(),
                "role": str(item.get("role", "")).strip(),
                "duration": str(item.get("duration", "")).strip(),
                "location": str(item.get("location", "")).strip(),
                "bullets": bullets,
            }
        )

    result["experience"] = clean_experience

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    projects = result.get("projects", [])
    if not isinstance(projects, list):
        projects = []

    clean_projects = []
    for item in projects:
        if not isinstance(item, dict):
            continue

        technologies = _safe_list(item.get("technologies"))
        bullets = _clean_bullet_list(item.get("bullets"))

        clean_projects.append(
            {
                "name": str(item.get("name", "")).strip(),
                "technologies": technologies,
                "bullets": bullets,
            }
        )

    result["projects"] = clean_projects

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    education = result.get("education", [])
    if not isinstance(education, list):
        education = []

    clean_education = []
    for item in education:
        if not isinstance(item, dict):
            continue

        clean_education.append(
            {
                "degree": str(item.get("degree", "")).strip(),
                "institution": str(item.get("institution", "")).strip(),
                "duration": str(item.get("duration", "")).strip(),
                "grade": str(item.get("grade", "")).strip(),
            }
        )

    result["education"] = clean_education

    return result