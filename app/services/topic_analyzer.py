import re
from app.models.structured_syllabus import Unit, Topic

# ---------------- Bloom's Verb Mapping ----------------
BLOOM_VERBS = {
    "define": 1,
    "list": 1,
    "explain": 2,
    "describe": 2,
    "apply": 3,
    "design": 3,
    "analyze": 4,
    "evaluate": 4,
    "optimize": 4
}

STOP_WORDS = {"and", "or", "the", "of", "to", "in", "for", "with"}


def count_subtopics(text: str) -> int:
    lines = text.split("\n")
    bullets = [
        line for line in lines
        if line.strip().startswith(("-", "•", "*")) or re.match(r"\d+\.", line)
    ]
    return max(len(bullets), 1)


def extract_bloom_verb(text: str) -> str:
    text = text.lower()
    found = [v for v in BLOOM_VERBS if v in text]
    return max(found, key=lambda v: BLOOM_VERBS[v]) if found else "define"


def count_concepts(text: str) -> int:
    words = re.split(r"[,\n]", text)
    concepts = [
        w.strip().lower()
        for w in words
        if w.strip().lower() not in STOP_WORDS and len(w.strip()) > 3
    ]
    return max(len(concepts), 1)


def estimate_dependency(unit_index: int) -> int:
    if unit_index == 1:
        return 1
    elif unit_index == 2:
        return 2
    return 3


# ---------------- Complexity Feature Extractor ----------------
def analyze_topic(topic_text: str, unit_index: int) -> dict:
    return {
        "subtopics": count_subtopics(topic_text),
        "verb": extract_bloom_verb(topic_text),
        "concepts": count_concepts(topic_text),
        "dependencies": estimate_dependency(unit_index),
        "weightage": None
    }


# ---------------- FIXED: Structured → Flat Topics ----------------
def extract_topics(structured_syllabus):
    topics = []

    INVALID_PREFIXES = ("unit", "module", "chapter")

    for unit_index, unit in enumerate(structured_syllabus, start=1):

        # ✅ Support both dicts and Pydantic models
        unit_topics = (
            unit.topics if hasattr(unit, "topics")
            else unit.get("topics", [])
        )

        for topic in unit_topics:
            title = (
                topic.title if hasattr(topic, "title")
                else topic.get("title", "")
            ).strip()

            # 🚫 Skip structural headings
            if title.lower().startswith(INVALID_PREFIXES):
                continue

            # 🚫 Skip junk
            if len(title) < 5:
                continue

            analysis = analyze_topic(title, unit_index)

            topics.append({
                "title": title,
                "unit_index": unit_index,
                **analysis
            })

    return topics

