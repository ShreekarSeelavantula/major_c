import re
from typing import List
from app.models.structured_syllabus import Unit, Topic


UNIT_PATTERNS = [
    r"UNIT\s+\d+",
    r"Unit\s+\d+",
    r"Module\s+\d+",
    r"Chapter\s+\d+"
]


def is_unit_heading(line: str) -> bool:
    for pattern in UNIT_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"[•●▪■]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def structure_syllabus(text: str) -> List[Unit]:
    lines = text.split("\n")

    units: List[Unit] = []
    current_unit = None

    for raw_line in lines:
        line = clean_line(raw_line)

        if len(line) < 4:
            continue

        # Detect unit heading
        if is_unit_heading(line):
            current_unit = Unit(unit_number=len(units) + 1, title=line, topics=[])
            units.append(current_unit)
            continue

        # Otherwise → topic
        if current_unit:
            current_unit.topics.append(
                Topic(title=line)
            )

    # Fallback: no units detected
    if not units:
        fallback_unit = Unit(
            unit_number=1,
            title="General Topics",
            topics=[Topic(title=clean_line(l)) for l in lines if len(clean_line(l)) > 4]
        )
        units.append(fallback_unit)

    return units
