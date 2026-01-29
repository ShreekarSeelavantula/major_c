# Bloom verb scores
VERB_SCORES = {
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


def compute_complexity(topic_features: dict) -> dict:
    """
    topic_features expects:
    {
        title: str,
        verb: str,
        subtopics: int,
        concepts: int,
        dependencies: int,
        unit_index: int
    }
    """

    # Base score from structure
    score = (
        topic_features.get("subtopics", 1) * 1 +
        topic_features.get("concepts", 1) * 1 +
        topic_features.get("dependencies", 0) * 2
    )

    # Bloom's taxonomy verb weight
    verb_weights = {
        "define": 1,
        "describe": 1,
        "explain": 2,
        "discuss": 2,
        "apply": 3,
        "compare": 3,
        "analyze": 4,
        "design": 4,
        "evaluate": 5,
        "create": 5
    }

    verb = topic_features.get("verb", "").lower()
    score += verb_weights.get(verb, 1)

    # Complexity classification
    if score <= 5:
        complexity = "Easy"
    elif score <= 9:
        complexity = "Medium"
    else:
        complexity = "Hard"

    return {
        "score": score,
        "complexity": complexity
    }

