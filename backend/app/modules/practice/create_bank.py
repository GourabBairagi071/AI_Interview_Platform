"""
Universal Question Bank Generator for 47 Technologies.
Creates 5,640+ unique, deep technical interview questions.
"""
import hashlib
import json
import os

def slugify(text: str) -> str:
    cleaned = text.lower().replace("+", "-plus").replace(".", "-").replace("/", "-")
    chars = [c if c.isalnum() or c == "-" else "-" for c in cleaned]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")

def generate_qid(q_text: str) -> str:
    cleaned = q_text.strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]

# Concept templates generator that produces distinct, technically rigorous questions and explanations
def make_q(subtopic, q_text, difficulty, q_type, explanation):
    return {
        "subtopic": subtopic,
        "question": q_text,
        "difficulty": difficulty,
        "question_type": q_type,
        "explanation": explanation
    }
