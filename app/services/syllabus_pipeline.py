from app.services.topic_analyzer import extract_topics
from app.services.complexity_engine import compute_complexity
from app.services.time_estimator import estimate_hours


def process_syllabus(structured_syllabus):
    """
    structured_syllabus: list of units (dict-based or pydantic-based)
    returns: list of topics with complexity + estimated study hours
    """

    topics = extract_topics(structured_syllabus)
    results = []

    for topic in topics:
        # 🧠 Complexity calculation
        complexity = compute_complexity(topic)

        topic_result = {
            "topic": topic["title"],
            "score": complexity["score"],
            "complexity": complexity["complexity"]
        }

        # ⏱️ Time estimation
        topic_result["estimated_hours"] = estimate_hours(topic_result)

        results.append(topic_result)

    return results
