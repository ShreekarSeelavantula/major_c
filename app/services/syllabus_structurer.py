import re
from typing import List
from app.models.structured_syllabus import Unit, Topic


# -----------------------------
# Patterns
# -----------------------------

UNIT_PATTERNS = [
    r"UNIT\s*[-–]?\s*[IVX\d]+",
    r"Unit\s*[-–]?\s*[IVX\d]+",
    r"Module\s*[-–]?\s*\d+",
    r"Chapter\s*[-–]?\s*\d+"
]

NOISE_PATTERNS = [
    r"^l\s*t\s*p\s*c$",
    r"credits?",
    r"semester",
    r"b\.?tech",
    r"engineering college",
    r"department of",
    r"university",
    r"total credits"
]


# -----------------------------
# Helpers
# -----------------------------

def is_unit_heading(line: str) -> bool:
    return any(re.search(p, line, re.IGNORECASE) for p in UNIT_PATTERNS)


def is_noise(line: str) -> bool:
    lower = line.lower()
    return any(re.search(p, lower) for p in NOISE_PATTERNS)


def clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"[•●▪■]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def clean_unit_title(line: str) -> str:
    # Keep UNIT label but remove trailing clutter
    return clean_line(line).rstrip(":").title()


# -----------------------------
# Core Structurer
# -----------------------------

def structure_syllabus(text: str) -> List[Unit]:
    lines = text.split("\n")

    units: List[Unit] = []
    current_unit: Unit | None = None

    for raw_line in lines:
        line = clean_line(raw_line)

        if len(line) < 4 or is_noise(line):
            continue

        # -----------------------------
        # UNIT detection
        # -----------------------------
        if is_unit_heading(line):
            current_unit = Unit(
                unit_number=len(units) + 1,
                title=clean_unit_title(line),
                topics=[]
            )
            units.append(current_unit)
            continue

        # -----------------------------
        # Topic detection
        # -----------------------------
        if current_unit:
            # Avoid dumping huge paragraphs as topics
            if len(line) > 180:
                continue

            current_unit.topics.append(
                Topic(title=line)
            )

    # -----------------------------
    # Fallback (no units found)
    # -----------------------------
    if not units:
        fallback_topics = [
            Topic(title=clean_line(l))
            for l in lines
            if len(clean_line(l)) > 6 and not is_noise(clean_line(l))
        ]

        units.append(
            Unit(
                unit_number=1,
                title="General Topics",
                topics=fallback_topics[:40]  # safety cap
            )
        )

    return units
