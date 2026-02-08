import re
from typing import Dict


# -------------------------
# Regex Patterns
# -------------------------

UNIT_PATTERN = re.compile(
    r"""
    (unit|module|chapter)      # keyword
    \s*[-:]?\s*               # optional dash or colon
    (\d+|[ivxlcdm]+)           # number OR roman numeral
    """,
    re.IGNORECASE | re.VERBOSE
)

TOPIC_PATTERN = re.compile(
    r"^\s*(\d+\.|•|\-|\*)\s+\w+",
    re.MULTILINE
)

NEGATIVE_KEYWORDS = [
    "resume",
    "curriculum vitae",
    "linkedin",
    "github",
    "experience",
    "skills",
    "phone",
    "email",
    "address"
]


# -------------------------
# Core Validator
# -------------------------

def analyze_syllabus(text: str) -> Dict:
    if not text or len(text.strip()) < 500:
        return {
            "is_syllabus": False,
            "reason": "Too little content",
            "confidence": 0.0
        }

    lower_text = text.lower()

    negative_hits = sum(1 for k in NEGATIVE_KEYWORDS if k in lower_text)
    unit_matches = len(UNIT_PATTERN.findall(text))
    topic_matches = len(TOPIC_PATTERN.findall(text))

    # HARD rejection: resume / profile-like docs
    if negative_hits >= 3 and unit_matches == 0:
        return {
            "is_syllabus": False,
            "reason": "Looks like non-academic document",
            "confidence": 0.2
        }

    # Accept if academic structure exists
    if unit_matches >= 1 or topic_matches >= 10:
        confidence = min(0.5 + unit_matches * 0.15, 1.0)
        return {
            "is_syllabus": True,
            "reason": "Structured syllabus detected",
            "confidence": round(confidence, 2)
        }

    return {
        "is_syllabus": False,
        "reason": "No syllabus structure found",
        "confidence": 0.3
    }


def is_valid_syllabus(text: str) -> bool:
    return analyze_syllabus(text)["is_syllabus"]


if __name__ == "__main__":
    pass
