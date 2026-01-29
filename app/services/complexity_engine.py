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


def compute_complexity(topic: dict):
    """
    topic = {
        title,
        subtopics,
        verb,
        concepts,
        dependencies,
        weightage
    }
    """

    score = 0

    # 1️⃣ Subtopics
    if topic["subtopics"] <= 2:
        score += 1
    elif topic["subtopics"] <= 4:
        score += 2
    else:
        score += 3

    # 2️⃣ Bloom verb
    score += VERB_SCORES.get(topic["verb"], 2)

    # 3️⃣ Concept density
    if topic["concepts"] <= 2:
        score += 1
    elif topic["concepts"] <= 4:
        score += 2
    else:
        score += 3

    # 4️⃣ Dependency level
    score += topic["dependencies"]

    # 5️⃣ Weightage (optional)
    if topic.get("weightage"):
        w = topic["weightage"]
        if w > 10:
            score += 3
        elif w >= 5:
            score += 2
        else:
            score += 1

    # 🔍 Final classification
    if score <= 6:
        complexity = "Easy"
    elif score <= 10:
        complexity = "Medium"
    else:
        complexity = "Hard"

    return {
        "score": score,
        "complexity": complexity
    }
