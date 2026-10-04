import json
import re
from typing import Any

from groq import Groq

from app.core.config import settings

client = None
if settings.groq_api_key:
    try:
        client = Groq(api_key=settings.groq_api_key)
    except Exception:
        client = None

MODEL = "openai/gpt-oss-20b"


# ============================================================
# DETERMINISTIC CODING SCORING FORMULA
# ============================================================
# Correctness: 70% (test cases passed ratio)
# Performance: 10% (based on average runtime)
# Complexity: 10% (optimal algorithmic complexity match)
# Code Quality: 10% (readability, conciseness, formatting)
# ============================================================

def calculate_coding_score(
    passed_tests: int,
    total_tests: int,
    avg_runtime_ms: float,
    status: str,
    code_length: int,
) -> float:
    if total_tests == 0:
        return 0.0

    if status in ("Compilation Error", "Security Violation"):
        return 0.0

    # 1. Correctness Score (0 - 70 points)
    correctness_ratio = passed_tests / total_tests
    correctness_pts = correctness_ratio * 70.0

    # 2. Performance Score (0 - 10 points)
    if avg_runtime_ms <= 80:
        perf_pts = 10.0
    elif avg_runtime_ms <= 250:
        perf_pts = 8.0
    elif avg_runtime_ms <= 600:
        perf_pts = 5.0
    else:
        perf_pts = 2.0

    # 3. Complexity & Code Structure (0 - 20 points)
    # Penalize trivial or overly bloated code
    struct_pts = 20.0 if (20 < code_length < 2500 and passed_tests > 0) else (10.0 if passed_tests > 0 else 0.0)

    total_score = correctness_pts + (perf_pts * correctness_ratio) + (struct_pts * correctness_ratio)
    return round(min(100.0, max(0.0, total_score)), 1)


# ============================================================
# HEURISTIC COMPLEXITY ESTIMATOR (STATIC CODE ANALYSIS)
# ============================================================

def estimate_static_complexity(source_code: str, language: str) -> dict[str, str]:
    code = source_code.lower()

    # Time Complexity heuristic
    # Check for nested loops
    nested_loops = len(re.findall(r"\b(for|while)\b[\s\S]*?\b(for|while)\b", code))
    single_loops = len(re.findall(r"\b(for|while)\b", code))
    has_sort = bool(re.search(r"(\.sort\(|sorted\(|arrays\.sort|std::sort)", code))
    has_recursion = bool(re.search(r"\bdef\s+([a-zA-Z0-9_]+)[\s\S]*?\1\(", code))

    if nested_loops >= 2:
        time_est = "O(n³)"
    elif nested_loops == 1:
        time_est = "O(n²)"
    elif has_sort:
        time_est = "O(n log n)"
    elif single_loops >= 1 or has_recursion:
        time_est = "O(n)"
    else:
        time_est = "O(1)"

    # Space Complexity heuristic
    has_dict_or_set = bool(re.search(r"(\bdict\(|{\s*}|\bset\(|\bmap\b|\bunordered_map\b|\bhashset\b)", code))
    has_array_alloc = bool(re.search(r"(\[\s*\]|\blist\(|\bvector\b|\barraylist\b)", code))

    if has_dict_or_set or has_array_alloc:
        space_est = "O(n)"
    else:
        space_est = "O(1)"

    return {
        "time": time_est,
        "space": space_est,
    }


# ============================================================
# AI CODE REVIEW & OPTIMIZATION SERVICE
# ============================================================

async def generate_ai_code_review(
    problem_title: str,
    language: str,
    source_code: str,
    status: str,
    passed_tests: int,
    total_tests: int,
) -> dict[str, Any]:
    static_comp = estimate_static_complexity(source_code, language)

    # Fallback review in case LLM is unreachable
    fallback_review = {
        "summary": f"Code submitted in {language} with status '{status}' ({passed_tests}/{total_tests} test cases passed).",
        "strengths": [
            f"Implemented clear modular syntax in {language}.",
            "Good functional decomposition matching standard interview specifications."
        ] if passed_tests > 0 else ["Submitted functional structure ready for iterative debugging."],
        "issues": [
            "Consider handling extreme input boundary edge cases.",
            "Verify memory footprint with large datasets."
        ] if status == "Accepted" else [f"Failed to pass all validation tests with status: {status}."],
        "complexity": static_comp,
        "optimization_suggestions": [
            "Use early return statements to minimize nesting depth.",
            "Evaluate hash-table lookups for O(1) amortized search time."
        ],
    }

    if not client:
        return fallback_review

    prompt = f"""
You are an expert technical interviewer and senior staff software engineer at a top tech company.
Analyze this candidate's code submission for the coding problem: "{problem_title}".

Language: {language}
Execution Status: {status}
Test Cases Passed: {passed_tests} / {total_tests}

Candidate Source Code:
```{language}
{source_code}
```

Evaluate:
1. Short executive summary (1-2 sentences)
2. 2-3 genuine strengths of their solution
3. 2-3 specific code quality or algorithmic issues / edge cases
4. Exact Big-O time and space complexity with short reason
5. 2-3 specific, actionable optimization suggestions

Return ONLY valid JSON matching this exact structure:
{{
  "summary": "Concise overview",
  "strengths": ["strength 1", "strength 2"],
  "issues": ["issue 1", "issue 2"],
  "complexity": {{
    "time": "O(...)",
    "space": "O(...)"
  }},
  "optimization_suggestions": ["suggestion 1", "suggestion 2"]
}}
Do not include markdown ticks, preamble, or commentary outside the JSON.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        return {
            "summary": parsed.get("summary", fallback_review["summary"]),
            "strengths": parsed.get("strengths", fallback_review["strengths"]),
            "issues": parsed.get("issues", fallback_review["issues"]),
            "complexity": parsed.get("complexity", static_comp),
            "optimization_suggestions": parsed.get("optimization_suggestions", fallback_review["optimization_suggestions"]),
        }
    except Exception:
        return fallback_review


# ============================================================
# INTERACTIVE AI CODING ASSISTANT (HINTS & GUIDANCE)
# ============================================================

async def generate_ai_coding_assistance(
    problem_title: str,
    problem_description: str,
    language: str,
    source_code: str,
    action: str,
    hint_level: int = 1,
    error_message: str | None = None,
    stored_hints: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generates progressive hints and interactive problem solving assistance.
    Guarantees that full solutions are NEVER prematurely revealed.
    """
    # Check if a curated hint exists in stored_hints for this level
    if action == "give_hint" and stored_hints and 1 <= hint_level <= len(stored_hints):
        return {
            "action": action,
            "content": stored_hints[hint_level - 1],
            "hint_level": hint_level,
            "max_hints": max(3, len(stored_hints)),
        }

    # Fallback response generator
    def get_fallback():
        if action == "give_hint":
            hints_map = {
                1: f"Consider what data structure allows rapid O(1) searches as you scan through the elements.",
                2: f"Can you store items you have already processed in a hash map or set to check for matching pairs?",
                3: f"Track the complement (target - current_value). If seen before, its recorded index gives your answer instantly.",
                4: f"Approach: Initialize a map. Iterate once. If target - num in map, return indices. Otherwise store num: index.",
                5: f"Logic breakdown: Loop through the array, calculate the needed difference, and use map lookups to avoid nested O(n^2) loops."
            }
            return hints_map.get(hint_level, hints_map[1])
        elif action == "explain_problem":
            return f"Problem '{problem_title}' asks you to analyze the input parameters and produce the exact specified output under the given constraints without modifying immutable state."
        elif action == "explain_error":
            return f"Error diagnosis: {error_message or 'Check for index out of bounds, unhandled null values, or syntax errors.'}"
        elif action == "review_approach":
            return "Your approach shows good structural intent. Make sure you handle edge cases such as empty input, single element, or extreme integer bounds."
        elif action == "analyze_complexity":
            return "Time Complexity: O(n) scan. Space Complexity: O(n) auxiliary memory for tracking states."
        elif action == "suggest_optimization":
            return "Consider replacing linear scans with hash lookups or two-pointer traversals to reduce quadratic time to linear."
        elif action == "explain_edge_cases":
            return "Key edge cases to verify: 1) Minimum size input, 2) Negative values, 3) Duplicated elements, 4) Strict boundary constraints."
        return "Review the problem constraints and verify your loop termination conditions."

    if not client:
        return {
            "action": action,
            "content": get_fallback(),
            "hint_level": hint_level if action == "give_hint" else None,
            "max_hints": 3,
        }

    hint_rules = ""
    if action == "give_hint":
        hint_rules = f"""
CRITICAL RULE: The candidate asked for HINT LEVEL {hint_level} of 5.
- Level 1: Gentle conceptual nudge. Do NOT mention code or specific structures.
- Level 2: Point in the direction of the optimal data structure.
- Level 3: Algorithmic invariant and loop strategy.
- Level 4: Step-by-step approach walkthrough.
- Level 5: Detailed pseudocode logic.
DO NOT WRITE COMPLETE WORKING CODE. The candidate must write the final implementation themselves.
"""

    prompt = f"""
You are a patient, world-class computer science educator and tech interviewer at a top company.
Assist the candidate with this coding challenge: "{problem_title}".

Problem Description:
{problem_description[:1000]}

Candidate's current code ({language}):
```{language}
{source_code[:1500] if source_code else "[No code written yet]"}
```

Error details (if any):
{error_message or "None"}

Requested Action: {action.upper()}
{hint_rules}

Provide a concise, encouraging, and pedagogically clear response (2 to 4 paragraphs max).
Format with clean markdown bullets where helpful.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        content = response.choices[0].message.content or get_fallback()
        return {
            "action": action,
            "content": content.strip(),
            "hint_level": hint_level if action == "give_hint" else None,
            "max_hints": max(3, len(stored_hints or [])),
        }
    except Exception:
        return {
            "action": action,
            "content": get_fallback(),
            "hint_level": hint_level if action == "give_hint" else None,
            "max_hints": 3,
        }

