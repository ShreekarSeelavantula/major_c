import re

SYLLABUS_KEYWORDS = [
    "syllabus", "course objectives", "course outcomes",
    "unit", "module", "credits", "evaluation",
    "textbooks", "reference", "semester", "marks"
]

NEGATIVE_KEYWORDS = [
    "resume", "curriculum vitae", "skills",
    "projects", "experience", "linkedin",
    "github", "phone", "email"
]


def is_valid_syllabus(text: str) -> bool:
    if not text or len(text.strip()) < 300:
        return False

    text_lower = text.lower()

    positive_score = sum(1 for kw in SYLLABUS_KEYWORDS if kw in text_lower)
    negative_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)

    # structural signal
    unit_pattern = re.findall(r"(unit|module)\s*[–\-]?\s*\d+", text_lower)

    if positive_score >= 3 and len(unit_pattern) >= 2 and negative_score <= 2:
        return True

    return False
