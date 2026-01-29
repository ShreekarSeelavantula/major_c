from typing import List
from app.models.structured_syllabus import Unit, Topic


def structure_syllabus(extracted_text: str) -> List[Unit]:
    """
    Converts extracted syllabus text into structured units & topics
    """

    lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]

    units: List[Unit] = []
    current_topics: List[Topic] = []
    unit_counter = 1

    for line in lines:
        # Simple heuristic: detect UNIT headings
        if line.lower().startswith(("unit", "module")):
            if current_topics:
                units.append(
                    Unit(
                        unit_number=unit_counter,
                        title=f"Unit {unit_counter}",
                        topics=current_topics
                    )
                )
                unit_counter += 1
                current_topics = []
        else:
            current_topics.append(Topic(title=line))

    # fallback / last unit
    if current_topics:
        units.append(
            Unit(
                unit_number=unit_counter,
                title=f"Unit {unit_counter}",
                topics=current_topics
            )
        )

    # Absolute fallback
    if not units:
        units.append(
            Unit(
                unit_number=1,
                title="General Topics",
                topics=[Topic(title=extracted_text[:200])]
            )
        )

    return units
