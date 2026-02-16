from typing import List
from app.models.structured_syllabus import Unit


DEFAULT_COMPLEXITY = "Medium"
DEFAULT_TOPIC_HOURS = 1.5


def convert_units_to_planner_topics(units: List[Unit]):

    planner_topics = []

    for unit in units:
        for topic in unit.topics:

            planner_topics.append({
                "topic": topic.title,
                "complexity": DEFAULT_COMPLEXITY,
                "estimated_hours": DEFAULT_TOPIC_HOURS
            })

    return planner_topics
