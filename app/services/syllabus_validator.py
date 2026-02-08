import re
from typing import List, Dict

ACADEMIC_KEYWORDS = [
    "syllabus",
    "course objectives",
    "course outcomes",
    "unit",
    "semester",
    "credits",
    "b.tech",
    "engineering",
    "department"
]

NEGATIVE_KEYWORDS = [
    "resume",
    "curriculum vitae",
    "linkedin",
    "github",
    "experience",
    "skills",
    "phone",
    "email"
]


def analyze_syllabus(text: str) -> Dict:
    if not text or len(text.strip()) < 200:
        return {
            "is_syllabus": False,
            "reason": "Too little text extracted",
            "confidence": 0.0
        }

    lower = text.lower()

    academic_hits = sum(1 for k in ACADEMIC_KEYWORDS if k in lower)
    negative_hits = sum(1 for k in NEGATIVE_KEYWORDS if k in lower)

    # HARD rule: reject only obvious non-academic docs
    if negative_hits >= 4 and academic_hits <= 1:
        return {
            "is_syllabus": False,
            "reason": "Document looks non-academic",
            "confidence": 0.2
        }

    # Otherwise ACCEPT
    confidence = min(0.4 + academic_hits * 0.1, 1.0)

    return {
        "is_syllabus": True,
        "reason": "Academic syllabus detected",
        "confidence": round(confidence, 2)
    }


def is_valid_syllabus(text: str) -> bool:
    return analyze_syllabus(text)["is_syllabus"]
