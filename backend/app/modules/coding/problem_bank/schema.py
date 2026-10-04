import re
from typing import Any
from pydantic import BaseModel, Field, field_validator


def slugify(text: str) -> str:
    """Generates clean url-friendly kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class TestPair(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class ProblemRecord(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    slug: str | None = None
    description: str = Field(min_length=10)
    difficulty: str = Field(default="Medium")
    topic: str = Field(default="Algorithms", max_length=100)
    tags: list[str] = Field(default_factory=list)
    company_tags: list[str] = Field(default_factory=list)
    role_tags: list[str] = Field(default_factory=list)
    constraints: list[str] | str | None = None
    input_format: str | None = None
    output_format: str | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)
    starter_code: dict[str, str] = Field(default_factory=dict)
    supported_languages: list[str] = Field(default_factory=lambda: ["python", "javascript", "cpp", "java"])
    public_test_cases: list[dict[str, Any]] = Field(default_factory=list)
    hidden_test_cases: list[dict[str, Any]] = Field(default_factory=list)
    expected_time_complexity: str | None = None
    expected_space_complexity: str | None = None
    editorial: str | None = None
    hints: list[str] = Field(default_factory=list)

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> str:
        s = str(v).strip().capitalize()
        if s.lower() in ("easy", "e"):
            return "Easy"
        elif s.lower() in ("hard", "h"):
            return "Hard"
        return "Medium"

    @field_validator("topic", mode="before")
    @classmethod
    def normalize_topic(cls, v: Any) -> str:
        if not v:
            return "General"
        return str(v).strip()

    @field_validator("slug", mode="before")
    @classmethod
    def ensure_slug(cls, v: Any, info: Any) -> str:
        if v and str(v).strip():
            return slugify(str(v))
        title = info.data.get("title") if info and hasattr(info, "data") else None
        if title:
            return slugify(str(title))
        return "problem"


class ImportReport(BaseModel):
    total_records: int = 0
    imported: int = 0
    skipped: int = 0
    duplicates: int = 0
    invalid: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
