import json

from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.groq_api_key
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# 1. GENERATE MAIN INTERVIEW QUESTIONS
# ============================================================

async def generate_interview_questions(
    job_role: str,
    difficulty: str,
    number_of_questions: int = 5,
) -> list[dict]:

    prompt = f"""
You are an expert technical interviewer.

Generate {number_of_questions} interview questions for the role:
{job_role}

Difficulty:
{difficulty}

The questions should:

- Be relevant to the job role
- Test conceptual understanding
- Test practical understanding
- Test problem-solving ability
- Avoid duplicate questions
- Match the requested difficulty
- Cover different relevant topics

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations.

Format:

[
  {{
    "question": "Question text",
    "topic": "Topic",
    "difficulty": "{difficulty}"
  }}
]
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert technical interviewer "
                    "who creates high-quality interview questions."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "AI returned an empty response"
        )

    try:
        questions = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "AI returned invalid JSON"
        ) from exc

    if not isinstance(questions, list):
        raise ValueError(
            "AI response must be a list"
        )

    return questions


# ============================================================
# 2. GENERATE ADAPTIVE FOLLOW-UP QUESTION
# ============================================================

async def generate_followup_question(
    job_role: str,
    question: str,
    answer: str,
    conversation_history: list[dict] | None = None,
) -> dict:

    history = conversation_history or []

    prompt = f"""
You are an expert technical interviewer conducting a live interview.

Job Role:
{job_role}

Current Question:
{question}

Candidate Answer:
{answer}

Previous Conversation:
{json.dumps(history, ensure_ascii=False)}

Analyze the candidate's answer carefully.

============================================================
CANDIDATE PERFORMANCE
============================================================

Classify the answer internally as:

strong:
- Technically correct
- Detailed
- Clear
- Demonstrates strong understanding
- Includes reasoning or practical examples

average:
- Mostly correct
- Some understanding is demonstrated
- Missing important details
- Needs more depth or clarification

weak:
- Incorrect
- Very incomplete
- Confused
- Demonstrates weak understanding

============================================================
FOLLOW-UP DECISION
============================================================

Generate a follow-up question when:

- The answer is incomplete
- More technical depth is required
- The candidate makes a claim requiring clarification
- The candidate mentions a technology without explaining it
- The candidate demonstrates partial understanding
- Deeper evaluation would be useful

Do NOT generate a follow-up when:

- The answer is sufficiently complete
- The candidate has demonstrated strong enough understanding
- Another question would be repetitive

============================================================
ADAPTIVE DIFFICULTY
============================================================

If the candidate is STRONG:

- Ask a harder follow-up
- Test deeper understanding
- Test edge cases
- Test practical application
- difficulty = "hard"

If the candidate is AVERAGE:

- Ask a clarification or depth question
- Keep moderate difficulty
- difficulty = "medium"

If the candidate is WEAK:

- Ask a simpler conceptual question
- Test fundamental understanding
- difficulty = "easy"

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

If a follow-up is required:

{{
    "should_follow_up": true,
    "question": "One concise follow-up question",
    "reason": "Short explanation",
    "difficulty": "hard"
}}

If no follow-up is required:

{{
    "should_follow_up": false,
    "question": "",
    "reason": "Short explanation",
    "difficulty": "medium"
}}

Rules:

- difficulty must be exactly "easy", "medium", or "hard"
- Generate only ONE follow-up question
- Never generate multiple questions
- Do not include markdown
- Do not include additional fields
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional adaptive technical "
                    "interviewer. Dynamically adjust question "
                    "difficulty based on candidate performance."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "AI returned an empty follow-up response"
        )

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "AI returned invalid follow-up JSON"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Follow-up response must be an object"
        )

    difficulty = str(
        result.get(
            "difficulty",
            "medium",
        )
    ).lower()

    if difficulty not in {
        "easy",
        "medium",
        "hard",
    }:
        difficulty = "medium"

    should_follow_up = bool(
        result.get(
            "should_follow_up",
            False,
        )
    )

    followup_question = str(
        result.get(
            "question",
            "",
        )
    ).strip()

    reason = str(
        result.get(
            "reason",
            "",
        )
    ).strip()

    if not should_follow_up:
        followup_question = ""

    return {
        "should_follow_up": should_follow_up,
        "question": followup_question,
        "reason": reason,
        "difficulty": difficulty,
    }


# ============================================================
# 3. EVALUATE COMPLETE INTERVIEW
#    Includes QUESTION-LEVEL EVALUATION
# ============================================================

async def evaluate_interview_answers(
    job_role: str,
    questions: list[dict],
    answers: str,
) -> dict:

    prompt = f"""
You are an expert technical interviewer.

Job Role:
{job_role}

Interview Questions:
{json.dumps(questions, ensure_ascii=False)}

Candidate Answers:
{answers}

Evaluate EVERY interview question separately.

============================================================
QUESTION-LEVEL EVALUATION
============================================================

For every question evaluate:

1. Technical correctness
2. Relevance
3. Depth
4. Clarity
5. Problem-solving ability
6. Practical understanding

Give every question a score from 0 to 100.

Then calculate the overall interview score.

============================================================
OVERALL EVALUATION
============================================================

Also evaluate:

- Overall technical ability
- Problem-solving ability
- Communication
- Practical knowledge
- Strengths
- Weaknesses
- Areas for improvement

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
    "score": 0,

    "feedback": "Overall feedback about the candidate's performance",

    "strengths": [
        "strength 1",
        "strength 2"
    ],

    "weaknesses": [
        "weakness 1",
        "weakness 2"
    ],

    "question_evaluations": [
        {{
            "question_number": 1,
            "score": 0,
            "feedback": "Specific feedback for this answer",
            "strengths": [
                "strength"
            ],
            "weaknesses": [
                "weakness"
            ]
        }}
    ]
}}

Rules:

- Evaluate EVERY question.
- question_number starts from 1.
- There must be one evaluation for every question.
- score must be between 0 and 100.
- Overall score must be between 0 and 100.
- Do not skip questions.
- Do not invent candidate answers.
- Feedback must be based on the actual candidate answer.
- Do not include markdown.
- Do not include anything outside JSON.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert technical interviewer "
                    "and professional interview evaluator."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "AI returned an empty evaluation"
        )

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "AI returned invalid evaluation JSON"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Evaluation response must be an object"
        )

    # ========================================================
    # NORMALIZE OVERALL SCORE
    # ========================================================

    try:
        score = float(
            result.get(
                "score",
                0,
            )
        )
    except (TypeError, ValueError):
        score = 0.0

    score = max(
        0.0,
        min(
            100.0,
            score,
        ),
    )

    # ========================================================
    # NORMALIZE QUESTION EVALUATIONS
    # ========================================================

    raw_evaluations = result.get(
        "question_evaluations",
        [],
    )

    if not isinstance(
        raw_evaluations,
        list,
    ):
        raw_evaluations = []

    normalized_evaluations = []

    for index, evaluation in enumerate(
        raw_evaluations,
        start=1,
    ):

        if not isinstance(
            evaluation,
            dict,
        ):
            continue

        try:
            question_number = int(
                evaluation.get(
                    "question_number",
                    index,
                )
            )
        except (TypeError, ValueError):
            question_number = index

        try:
            question_score = float(
                evaluation.get(
                    "score",
                    0,
                )
            )
        except (TypeError, ValueError):
            question_score = 0.0

        question_score = max(
            0.0,
            min(
                100.0,
                question_score,
            ),
        )

        strengths = evaluation.get(
            "strengths",
            [],
        )

        if not isinstance(
            strengths,
            list,
        ):
            strengths = []

        weaknesses = evaluation.get(
            "weaknesses",
            [],
        )

        if not isinstance(
            weaknesses,
            list,
        ):
            weaknesses = []

        normalized_evaluations.append(
            {
                "question_number": question_number,
                "score": question_score,
                "feedback": str(
                    evaluation.get(
                        "feedback",
                        "",
                    )
                ),
                "strengths": strengths,
                "weaknesses": weaknesses,
            }
        )

    # ========================================================
    # RETURN FINAL RESULT
    # ========================================================

    return {
        "score": score,

        "feedback": str(
            result.get(
                "feedback",
                "",
            )
        ),

        "strengths": (
            result.get(
                "strengths",
                [],
            )
            if isinstance(
                result.get(
                    "strengths",
                    [],
                ),
                list,
            )
            else []
        ),

        "weaknesses": (
            result.get(
                "weaknesses",
                [],
            )
            if isinstance(
                result.get(
                    "weaknesses",
                    [],
                ),
                list,
            )
            else []
        ),

        "question_evaluations": (
            normalized_evaluations
        ),
    }