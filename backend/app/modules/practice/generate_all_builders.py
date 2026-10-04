"""
Programmatic generator for the 7 bank builder modules.
Crafts 5,640+ unique, deep technical interview questions across all 47 technologies.
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILDERS_DIR = os.path.join(BASE_DIR, "bank_builders")
os.makedirs(BUILDERS_DIR, exist_ok=True)

print(f"Generating into {BUILDERS_DIR}")
