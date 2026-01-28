import re

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

STOP_WORDS = {
    "and", "or", "the", "of", "to", "in", "for", "with"
}


# ---------------- Subtopic Counter ----------------
def count_subtopics(text: str) -> int:
    """
    Counts bullet points, numbered lists, or line breaks
    """
    lines = text.split("\n")
    bullets = [
        line for line in lines
        if line.strip().startswith(("-", "•", "*")) or re.match(r"\d+\.", line)
    ]
    return max(len(bullets), 1)


# ---------------- Verb Extractor ----------------
def extract_bloom_verb(text: str) -> str:
    """
    Finds highest-order Bloom verb in text
    """
    text_lower = text.lower()
    found_verbs = []

    for verb in BLOOM_VERBS:
        if verb in text_lower:
            found_verbs.append(verb)

    if not found_verbs:
        return "define"  # safe default

    # Return highest cognitive verb
    return max(found_verbs, key=lambda v: BLOOM_VERBS[v])


# ---------------- Concept Density ----------------
def count_concepts(text: str) -> int:
    """
    Counts technical terms using commas and noun phrases
    """
    words = re.split(r"[,\n]", text)
    concepts = []

    for word in words:
        clean = word.strip().lower()
        if clean and clean not in STOP_WORDS and len(clean) > 3:
            concepts.append(clean)

    return max(len(concepts), 1)


# ---------------- Dependency Estimation ----------------
def estimate_dependency(unit_index: int) -> int:
    """
    Earlier units are easier, later units depend more
    """
    if unit_index == 1:
        return 1
    elif unit_index == 2:
        return 2
    else:
        return 3


# ---------------- Main Analyzer ----------------
def analyze_topic(topic_text: str, unit_index: int) -> dict:
    subtopics = count_subtopics(topic_text)
    verb = extract_bloom_verb(topic_text)
    concepts = count_concepts(topic_text)
    dependency = estimate_dependency(unit_index)

    return {
        "subtopics": subtopics,
        "verb": verb,
        "concepts": concepts,
        "dependencies": dependency,
        "weightage": None  # future use
    }
