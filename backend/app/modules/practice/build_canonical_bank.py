"""
Build Canonical Bank - Master script for generating 5,640+ questions across 47 technologies.
"""
import os
import sys
import json
import hashlib

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

print("Script template ready")
