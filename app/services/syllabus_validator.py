import re
from typing import List, Dict

# -----------------------------
# Keywords
# -----------------------------

SYLLABUS_KEYWORDS = [
    "syllabus",
    "course objectives",
    "course outcomes",
    "unit",
    "module",
    "credits",
    "semester"
]

NEGATIVE_KEYWORDS = [
    "resume", "curriculum vitae", "skills",
    "projects", "experience", "linkedin",
    "github", "phone", "email"
]

SUBJECT_HINT_KEYWORDS = [
    "course title", "subject title", "paper title"
]

# -----------------------------
# Helpers
# -----------------------------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _extract_subject_candidates(lines: List[str]) -> List[str]:
    """
    Extract likely subject titles without being overly aggressive
    """
    candidates = []

    for i, line in enumerate(lines):
        clean = _normalize(line)

        if len(clean) < 6 or len(clean) > 120:
            continue

        # ALL CAPS subject names (common in Indian syllabi)
        if clean.isupper() and 2 <= len(clean.split()) <= 10:
            candidates.append(clean.title())
            continue

        # Explicit labels
        if any(k in clean.lower() for k in SUBJECT_HINT_KEYWORDS):
            if i + 1 < len(lines):
                next_line = _normalize(lines[i + 1])
                if 6 < len(next_line) < 100:
                    candidates.append(next_line)

    # Deduplicate
    seen = set()
    unique = []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)

    return unique


def _count_unit_resets(text_lower: str) -> int:
    """
    UNIT 1 restarting may indicate multiple subjects
    """
    return len(re.findall(r"(unit|module)\s*[-–]?\s*1", text_lower))


# -----------------------------
# Core Analyzer
# -----------------------------

def analyze_syllabus(text: str) -> Dict:
    if not text or len(text.strip()) < 300:
        return {
            "is_syllabus": False,
            "confidence": 0.0,
            "has_multiple_subjects": False,
            "subjects": [],
            "reason": "Text too short"
        }

    text_lower = text.lower()
    lines = text.splitlines()

    positive_score = sum(1 for kw in SYLLABUS_KEYWORDS if kw in text_lower)
    negative_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)

    unit_occurrences = re.findall(r"(unit|module)\s*[–\-]?\s*\d+", text_lower)
    unit_resets = _count_unit_resets(text_lower)

    subjects = _extract_subject_candidates(lines)

    # -----------------------------
    # Confidence calculation
    # -----------------------------

    confidence = 0.0
    confidence += min(positive_score * 0.2, 0.5)
    confidence += min(len(unit_occurrences) * 0.07, 0.35)
    confidence -= min(negative_score * 0.15, 0.3)

    confidence = max(0.0, min(confidence, 1.0))

    # -----------------------------
    # VALID SYLLABUS LOGIC (UPDATED)
    # -----------------------------

    is_syllabus = (
        confidence >= 0.5 and
        positive_score >= 2 and
        len(unit_occurrences) >= 1 and
        negative_score <= 3
    )

    has_multiple_subjects = (
        len(subjects) >= 2 or unit_resets >= 2
    )

    return {
        "is_syllabus": is_syllabus,
        "confidence": round(confidence, 2),
        "has_multiple_subjects": has_multiple_subjects,
        "subjects": subjects,
        "unit_count": len(unit_occurrences),
        "negative_signals": negative_score
    }


# -----------------------------
# Backward Compatibility
# -----------------------------

def is_valid_syllabus(text: str) -> bool:
    """
    Legacy API – DO NOT REMOVE
    """
    return analyze_syllabus(text)["is_syllabus"]
