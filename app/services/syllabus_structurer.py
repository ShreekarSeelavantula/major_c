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
    r"regulation",
    r"total credits"
]

STOP_SECTIONS = [
    "course objectives",
    "course outcomes",
    "text books",
    "textbooks",
    "reference books",
    "references"
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
    return clean_line(line).rstrip(":").title()


def looks_like_continuation(line: str) -> bool:
    return (
        line[0].islower()
        or line.startswith("(")
        or line.startswith(",")
        or line.startswith("-")
    )


def split_topics(line: str) -> List[str]:
    parts = [p.strip() for p in line.split(",") if len(p.strip()) > 4]
    return parts if len(parts) > 1 else [line]


def is_stop_section(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in STOP_SECTIONS)


def looks_like_heading(line: str) -> bool:
    return line.isupper() and len(line.split()) <= 6


# -----------------------------
# Core Structurer
# -----------------------------

def structure_syllabus(text: str) -> List[Unit]:
    lines = text.split("\n")

    units: List[Unit] = []
    current_unit: Unit | None = None
    last_topic: Topic | None = None
    stop_parsing = False

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line or len(line) < 4:
            continue

        # Stop parsing after objectives / books
        if is_stop_section(line):
            stop_parsing = True
            continue

        if stop_parsing or is_noise(line):
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
            last_topic = None
            continue

        # -----------------------------
        # Topic detection
        # -----------------------------
        if current_unit:
            # Reject large paragraphs
            if len(line) > 180:
                continue

            # Reject admin-style headings
            if looks_like_heading(line):
                continue

            # Continuation line
            if last_topic and looks_like_continuation(line):
                last_topic.title += " " + line
                continue

            # Split comma-based topics
            for t in split_topics(line):
                topic = Topic(title=t)
                current_unit.topics.append(topic)
                last_topic = topic

    # -----------------------------
    # Fallback (no units found)
    # -----------------------------
    if not units:
        fallback_topics = [
            Topic(title=clean_line(l))
            for l in lines
            if len(clean_line(l)) > 6
            and not is_noise(clean_line(l))
            and not is_stop_section(clean_line(l))
        ]

        units.append(
            Unit(
                unit_number=1,
                title="General Topics",
                topics=fallback_topics[:40]
            )
        )

    return units
