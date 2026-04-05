import re
from app.models.structured_syllabus import Unit, Topic

# ── Bloom's Verb Mapping ──
BLOOM_VERBS = {
    "define": 1,
    "list": 1,
    "describe": 1,
    "explain": 2,
    "discuss": 2,
    "apply": 3,
    "compare": 3,
    "analyze": 4,
    "design": 4,
    "evaluate": 5,
    "create": 5,
    "optimize": 4
}

STOP_WORDS = {"and", "or", "the", "of", "to", "in", "for", "with", "a", "an"}


def count_subtopics(text: str) -> int:
    """Count bullet points or numbered items as subtopics."""
    lines = text.split("\n")
    bullets = [
        line for line in lines
        if line.strip().startswith(("-", "•", "*")) or re.match(r"\d+\.", line.strip())
    ]
    return max(len(bullets), 1)


def extract_bloom_verb(text: str) -> str:
    """
    Find the highest-level Bloom's verb in the text.
    Returns the verb string (used by complexity_engine for scoring).
    """
    text_lower = text.lower()
    found = [v for v in BLOOM_VERBS if v in text_lower]

    if not found:
        return "define"   # default — lowest level

    # Return the verb with the highest Bloom score
    return max(found, key=lambda v: BLOOM_VERBS[v])


def count_concepts(text: str) -> int:
    """
    Count distinct technical concepts by splitting on commas and newlines.
    Filters out stop words and very short tokens.
    """
    parts = re.split(r"[,\n]", text)
    concepts = [
        p.strip().lower()
        for p in parts
        if p.strip().lower() not in STOP_WORDS and len(p.strip()) > 3
    ]
    return max(len(concepts), 1)


def estimate_dependency(unit_index: int) -> int:
    """
    Estimate dependency level from unit position.
    Later units depend on more prior knowledge.
    Returns 1 (none), 2 (some), or 3 (many).
    """
    if unit_index <= 1:
        return 1
    elif unit_index == 2:
        return 2
    return 3


def analyze_topic(topic_text: str, unit_index: int) -> dict:
    """
    Extract all complexity features for a topic.

    Returns a dict ready to be passed directly into compute_complexity():
    {
        "verb":         str,   — highest Bloom verb found
        "subtopics":    int,   — bullet/numbered item count
        "concepts":     int,   — distinct concept count
        "dependencies": int,   — dependency level 1-3
        "weightage":    None   — reserved for future use
    }
    """
    return {
        "verb":         extract_bloom_verb(topic_text),
        "subtopics":    count_subtopics(topic_text),
        "concepts":     count_concepts(topic_text),
        "dependencies": estimate_dependency(unit_index),
        "weightage":    None
    }


# ── Structured → Flat Topics (used by topic_analyzer routes) ──
def extract_topics(structured_syllabus):
    topics = []
    INVALID_PREFIXES = ("unit", "module", "chapter")

    for unit_index, unit in enumerate(structured_syllabus, start=1):

        unit_topics = (
            unit.topics if hasattr(unit, "topics")
            else unit.get("topics", [])
        )

        for topic in unit_topics:
            title = (
                topic.title if hasattr(topic, "title")
                else topic.get("title", "")
            ).strip()

            if title.lower().startswith(INVALID_PREFIXES):
                continue

            if len(title) < 5:
                continue

            analysis = analyze_topic(title, unit_index)

            topics.append({
                "title":       title,
                "unit_index":  unit_index,
                **analysis
            })

    return topics