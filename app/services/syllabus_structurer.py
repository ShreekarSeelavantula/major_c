import re
from typing import List
from app.models.structured_syllabus import Unit, Topic


# =================================================
# NORMALIZATION
# =================================================

DASHES = ["–", "—", "−"]


def normalize_text(text: str) -> str:
    for d in DASHES:
        text = text.replace(d, "-")
    return text


def clean_line(line: str) -> str:
    line = line.strip()
    line = normalize_text(line)
    line = re.sub(r"[•●▪■]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


# =================================================
# METADATA / NOISE FILTERS
# =================================================

METADATA_KEYWORDS = [
    "course objectives",
    "course outcomes",
    "l t p c",
    "credits"
]

NOISE_KEYWORDS = [
    "engineering college",
    "autonomous",
    "department of",
    "b.tech",
    "semester",
    "regulation",
    "course structure",
    "periods per week",
    "total credits",
]


def is_metadata(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in METADATA_KEYWORDS)


def is_noise(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in NOISE_KEYWORDS)


STOP_SECTIONS = [
    "text books",
    "textbooks",
    "reference books",
    "references"
]


def is_stop_section(line: str) -> bool:
    lower = line.lower()
    return any(k in lower for k in STOP_SECTIONS)


# =================================================
# SUBJECT ISOLATION
# =================================================

COURSE_CODE_REGEX = re.compile(
    r"^[A-Z]{2,4}\d{3,4}[A-Z]{0,2}\s*:\s*.+",
    re.IGNORECASE
)


def extract_primary_subject_text(text: str) -> str:
    """
    Extract text belonging to the first detected subject only.
    Prevents headers and other subjects from polluting syllabus.
    """
    lines = normalize_text(text).split("\n")

    subject_lines: List[str] = []
    collecting = False

    for line in lines:
        clean = line.strip()
        if not clean:
            continue

        if COURSE_CODE_REGEX.match(clean):
            collecting = True
            subject_lines.append(clean)
            continue

        if collecting:
            if is_stop_section(clean):
                break
            subject_lines.append(clean)

    return "\n".join(subject_lines) if len(subject_lines) > 30 else text


# =================================================
# UNIT & TOPIC PATTERNS
# =================================================

UNIT_REGEX = re.compile(
    r"^\s*UNIT\s*[-:]?\s*(I|II|III|IV|V|VI|VII|VIII|IX|X|\d+)\s*$",
    re.IGNORECASE
)


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


# =================================================
# CORE STRUCTURER (FINAL + STABLE)
# =================================================

def structure_syllabus(text: str) -> List[Unit]:
    # Step 1: isolate one subject
    text = extract_primary_subject_text(text)
    lines = text.split("\n")

    units: List[Unit] = []
    current_unit: Unit | None = None
    last_topic: Topic | None = None
    expecting_unit_title = False

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line or len(line) < 4:
            continue

        if is_noise(line) or is_metadata(line):
            continue

        # -------------------------------
        # UNIT DETECTION
        # -------------------------------
        if is_unit_heading(line):
            current_unit = Unit(
                unit_number=len(units) + 1,
                title="",
                topics=[]
            )
            units.append(current_unit)
            last_topic = None
            expecting_unit_title = True
            continue

        if not current_unit:
            continue

        # -------------------------------
        # UNIT TITLE (NEXT LINE AFTER UNIT)
        # -------------------------------
        if expecting_unit_title:
            if line.endswith(":"):
                current_unit.title = line.rstrip(":")
                expecting_unit_title = False
                continue
            else:
                current_unit.title = line
                expecting_unit_title = False
                continue

        # -------------------------------
        # IGNORE ADMIN HEADINGS
        # -------------------------------
        if looks_like_heading(line):
            continue

        if len(line) > 220:
            continue

        # -------------------------------
        # CONTINUATION LOGIC
        # -------------------------------
        if last_topic and not last_topic.title.endswith("."):
            last_topic.title += " " + line
            continue

        # -------------------------------
        # TOPIC EXTRACTION
        # -------------------------------
        for t in split_topics(line):
            topic = Topic(title=t)
            current_unit.topics.append(topic)
            last_topic = topic

    # -------------------------------
    # SAFETY FALLBACK (RARE)
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
