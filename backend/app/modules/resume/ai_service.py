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

    try:

        ats_score = float(
            result.get(
                "ats_score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        ats_score = 0

    result["ats_score"] = int(
        max(
            0,
            min(
                100,
                ats_score,
            ),
        )
    )

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
    # --------------------------------------------------------
    # Prevent oversized Groq requests
    # --------------------------------------------------------

    MAX_RESUME_CHARS = 7000

    resume_text = resume_text.strip()

    if len(resume_text) > MAX_RESUME_CHARS:
        resume_text = resume_text[
            :MAX_RESUME_CHARS
        ]

    prompt = f"""
You are an expert ATS resume analyzer and technical recruiter.

Analyze the following resume.

RESUME:
----------------
{resume_text}
----------------

Return ONLY valid JSON.

Use exactly this structure:

{{
  "ats_score": 0,
  "skills": [],
  "strengths": [],
  "weaknesses": [],
  "suggestions": [],
  "role_matching": [
    {{
      "role": "",
      "match": 0,
      "reason": ""
    }}
  ]
}}

Rules:

1. ats_score must be an integer from 0 to 100.

2. skills:
Extract only skills that are actually present
in the resume.

3. strengths:
Identify genuine strengths supported by the resume.

4. weaknesses:
Identify realistic weaknesses or missing areas.

5. suggestions:
Give practical improvements for increasing ATS
compatibility.

6. role_matching:
Evaluate suitable technical roles based only
on the resume.

Do not invent:
- companies
- degrees
- certifications
- technologies
- projects
- achievements
- experience
- metrics

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

            temperature=0.1,

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
    # Normalize ATS score
    # --------------------------------------------------------

    try:

        ats_score = float(
            result.get(
                "ats_score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        ats_score = 0


    result["ats_score"] = int(
        max(
            0,
            min(
                100,
                ats_score,
            ),
        )
    )


    # --------------------------------------------------------
    # Normalize lists
    # --------------------------------------------------------

    result["skills"] = _safe_list(
        result.get("skills")
    )

    result["strengths"] = _safe_list(
        result.get("strengths")
    )

    result["weaknesses"] = _safe_list(
        result.get("weaknesses")
    )

    result["suggestions"] = _safe_list(
        result.get("suggestions")
    )


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

    for item in role_matching:

        if not isinstance(
            item,
            dict,
        ):
            continue

        try:

            match = float(
                item.get(
                    "match",
                    0,
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
                ),
                "match": int(
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
                ),
            }
        )


    result["role_matching"] = (
        clean_roles
    )


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
You are an expert ATS resume writer and
technical recruiter.

TARGET JOB ROLE:
{target_role}

EXISTING RESUME:
----------------
{resume_text}
----------------

Create an ATS-optimized version of this resume
for the target job role.

IMPORTANT:

Never invent information.

Do NOT invent:
- companies
- job titles
- dates
- degrees
- universities
- certifications
- projects
- technologies
- skills
- achievements
- metrics

Only improve information already present.

You MAY:
- improve grammar
- improve wording
- improve bullet points
- reorganize sections
- prioritize relevant skills
- improve ATS keyword placement
- improve professional summary
- remove repetition
- make achievements clearer
- use strong action verbs

The generated resume should be realistic,
professional and ATS-friendly.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "estimated_ats_score": 0,
  "target_role": "{target_role}",
  "professional_summary": "",

  "skills": [],

  "experience": [
    {{
      "company": "",
      "role": "",
      "duration": "",
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
      "duration": ""
    }}
  ],

  "certifications": [],

  "keywords": [],

  "improvements": [],

  "missing_keywords": []
}}

Keep the output concise.

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

            max_completion_tokens=1800,

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

    try:

        ats_score = float(
            result.get(
                "estimated_ats_score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        ats_score = 0


    result["estimated_ats_score"] = int(
        max(
            0,
            min(
                100,
                ats_score,
            ),
        )
    )


    result["target_role"] = (
        target_role
    )


    # --------------------------------------------------------
    # Normalize simple lists
    # --------------------------------------------------------

    result["skills"] = _safe_list(
        result.get("skills")
    )

    result["certifications"] = _safe_list(
        result.get("certifications")
    )

    result["keywords"] = _safe_list(
        result.get("keywords")
    )

    result["improvements"] = _safe_list(
        result.get("improvements")
    )

    result["missing_keywords"] = _safe_list(
        result.get("missing_keywords")
    )


    # --------------------------------------------------------
    # Professional summary
    # --------------------------------------------------------

    result["professional_summary"] = str(
        result.get(
            "professional_summary",
            "",
        )
    ).strip()


    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    experience = result.get(
        "experience",
        [],
    )

    if not isinstance(
        experience,
        list,
    ):
        experience = []


    clean_experience = []


    for item in experience:

        if not isinstance(
            item,
            dict,
        ):
            continue


        bullets = _safe_list(
            item.get(
                "bullets"
            )
        )


        clean_experience.append(
            {
                "company": str(
                    item.get(
                        "company",
                        "",
                    )
                ).strip(),

                "role": str(
                    item.get(
                        "role",
                        "",
                    )
                ).strip(),

                "duration": str(
                    item.get(
                        "duration",
                        "",
                    )
                ).strip(),

                "bullets": bullets,
            }
        )


    result["experience"] = (
        clean_experience
    )


    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    projects = result.get(
        "projects",
        [],
    )

    if not isinstance(
        projects,
        list,
    ):
        projects = []


    clean_projects = []


    for item in projects:

        if not isinstance(
            item,
            dict,
        ):
            continue


        technologies = _safe_list(
            item.get(
                "technologies"
            )
        )

        bullets = _safe_list(
            item.get(
                "bullets"
            )
        )


        clean_projects.append(
            {
                "name": str(
                    item.get(
                        "name",
                        "",
                    )
                ).strip(),

                "technologies": (
                    technologies
                ),

                "bullets": bullets,
            }
        )


    result["projects"] = (
        clean_projects
    )


    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    education = result.get(
        "education",
        [],
    )

    if not isinstance(
        education,
        list,
    ):
        education = []


    clean_education = []


    for item in education:

        if not isinstance(
            item,
            dict,
        ):
            continue


        clean_education.append(
            {
                "degree": str(
                    item.get(
                        "degree",
                        "",
                    )
                ).strip(),

                "institution": str(
                    item.get(
                        "institution",
                        "",
                    )
                ).strip(),

                "duration": str(
                    item.get(
                        "duration",
                        "",
                    )
                ).strip(),
            }
        )


    result["education"] = (
        clean_education
    )


    return result