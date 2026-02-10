import re
from typing import List
from app.models.structured_syllabus import Unit, Topic


# -------------------------------------------------
# Normalization helpers
# -------------------------------------------------

DASHES = ["–", "—", "−"]


def normalize_text(text: str) -> str:
    for d in DASHES:
        text = text.replace(d, "-")
    return text


# -------------------------------------------------
# Patterns
# -------------------------------------------------

UNIT_REGEX = re.compile(
    r"^\s*UNIT\s*-\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|\d+)\s*$",
    re.IGNORECASE
)

STOP_SECTIONS = [
    "course objectives",
    "course outcomes",
    "text books",
    "textbooks",
    "reference books",
    "references"
]

NOISE_KEYWORDS = [
    "engineering college",
    "autonomous",
    "department of",
    "b.tech",
    "semester",
    "regulation",
    "credits",
    "course structure",
    "periods per week",
    "l t p c",
    "total credits",
]


# -------------------------------------------------
# Line utilities
# -------------------------------------------------

def clean_line(line: str) -> str:
    line = line.strip()
    line = normalize_text(line)
    line = re.sub(r"[•●▪■]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def is_noise(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in NOISE_KEYWORDS)


def is_stop_section(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in STOP_SECTIONS)


def is_unit_heading(line: str) -> bool:
    return bool(UNIT_REGEX.match(line))


def looks_like_heading(line: str) -> bool:
    return line.isupper() and len(line.split()) <= 6


def looks_like_continuation(line: str) -> bool:
    return (
        line[0].islower()
        or line.startswith("(")
        or line.startswith(",")
        or line.startswith("-")
    )


def split_topics(line: str) -> List[str]:
    parts = [p.strip() for p in line.split(",") if len(p.strip()) > 5]
    return parts if len(parts) > 1 else [line]


# -------------------------------------------------
# CORE STRUCTURER
# -------------------------------------------------

def structure_syllabus(text: str) -> List[Unit]:
    text = normalize_text(text)
    lines = text.split("\n")

    units: List[Unit] = []
    current_unit: Unit | None = None
    last_topic: Topic | None = None
    stop_parsing = False

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line or len(line) < 4:
            continue

        # Stop parsing after objectives/books
        if is_stop_section(line):
            stop_parsing = True
            continue

        if stop_parsing or is_noise(line):
            continue

        # -------------------------------
        # UNIT DETECTION
        # -------------------------------
        if is_unit_heading(line):
            current_unit = Unit(
                unit_number=len(units) + 1,
                title=line.title(),
                topics=[]
            )
            units.append(current_unit)
            last_topic = None
            continue

        # -------------------------------
        # TOPIC DETECTION
        # -------------------------------
        if not current_unit:
            continue

        # Ignore admin headings
        if looks_like_heading(line):
            continue

        # Ignore long paragraphs
        if len(line) > 220:
            continue

        # Continuation line
        if last_topic and looks_like_continuation(line):
            last_topic.title += " " + line
            continue

        for t in split_topics(line):
            topic = Topic(title=t)
            current_unit.topics.append(topic)
            last_topic = topic

    # -------------------------------
    # Safety fallback (rare)
    # -------------------------------
    if not units:
        units.append(
            Unit(
                unit_number=1,
                title="Syllabus Topics",
                topics=[
                    Topic(title=clean_line(l))
                    for l in lines
                    if len(clean_line(l)) > 6
                ][:30]
            )
        )

    return units
