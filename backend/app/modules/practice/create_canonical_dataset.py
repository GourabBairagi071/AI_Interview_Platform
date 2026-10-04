"""
Canonical Question Bank Generator for AI Interview Platform.
Generates 5,600+ authentic, distinct, high-quality interview questions
across all 47 requested technologies, structured by Technology -> Topic -> Subtopic -> Question.
"""
import hashlib
import json
import os
import re

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
