# Bloom's taxonomy verb weights
VERB_WEIGHTS = {
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


def compute_complexity(topic_features: dict) -> dict:
    """
    Compute complexity score and classification for a topic.

    topic_features expects:
    {
        "title":        str,
        "verb":         str,       — Bloom's verb extracted from topic text
        "subtopics":    int,       — number of subtopics / bullet points
        "concepts":     int,       — number of distinct concepts
        "dependencies": int,       — dependency level (1=none, 2=some, 3=many)
        "unit_index":   int        — used by topic_analyzer for dependency estimate
    }

    Returns:
    {
        "score":            int,
        "complexity":       str,   — "Easy" | "Medium" | "Hard"
        "verb_score":       int,
        "subtopic_score":   int,
        "density_score":    int,
        "dependency_score": int
    }
    """

    # ── Subtopic score (structural depth) ──
    subtopics = topic_features.get("subtopics", 1)
    if subtopics <= 2:
        subtopic_score = 1
    elif subtopics <= 4:
        subtopic_score = 2
    else:
        subtopic_score = 3

    # ── Verb score (Bloom's taxonomy) ──
    verb = topic_features.get("verb", "define").lower()
    verb_score = VERB_WEIGHTS.get(verb, 1)

    # ── Concept density score ──
    concepts = topic_features.get("concepts", 1)
    if concepts <= 2:
        density_score = 1
    elif concepts <= 4:
        density_score = 2
    else:
        density_score = 3

    # ── Dependency score ──
    dependencies = topic_features.get("dependencies", 1)
    # dependencies comes in as 1 / 2 / 3 from topic_analyzer
    dependency_score = max(1, min(3, int(dependencies)))

    # ── Total score ──
    total = subtopic_score + verb_score + density_score + dependency_score

    # ── Classification ──
    if total <= 6:
        complexity = "Easy"
    elif total <= 10:
        complexity = "Medium"
    else:
        complexity = "Hard"

    return {
        "score":            total,
        "complexity":       complexity,
        "verb_score":       verb_score,
        "subtopic_score":   subtopic_score,
        "density_score":    density_score,
        "dependency_score": dependency_score
    }