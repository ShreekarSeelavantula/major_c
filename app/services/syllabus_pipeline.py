from app.services.topic_analyzer import extract_topics
from app.services.complexity_engine import compute_complexity


def process_syllabus(structured_syllabus):
    topics = extract_topics(structured_syllabus)
    results = []

    for topic in topics:
        complexity = compute_complexity(topic)

        results.append({
            "topic": topic["title"],
            "score": complexity["score"],
            "complexity": complexity["complexity"]
        })

    return results
