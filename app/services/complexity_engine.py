from app.services.topic_analyzer import analyze_topic

# Bloom verb scores
VERB_SCORES = {
    "define": 1,
    "list": 1,
    "explain": 2,
    "describe": 2,
    "apply": 3,
    "design": 3,
    "analyze": 4,
    "optimize": 4
}


def compute_complexity(topic_text: str, unit_index: int = 1):
    features = analyze_topic(topic_text, unit_index)

    score = 0

    # 1️⃣ Subtopics
    subtopics = features["subtopics"]
    if subtopics <= 2:
        score += 1
    elif subtopics <= 4:
        score += 2
    else:
        score += 3

    # 2️⃣ Bloom verb
    verb = features["verb"]
    score += VERB_SCORES.get(verb, 2)

    # 3️⃣ Concept density
    concepts = features["concepts"]
    if concepts <= 2:
        score += 1
    elif concepts <= 4:
        score += 2
    else:
        score += 3

    # 4️⃣ Dependency level
    score += features["dependencies"]

    # 5️⃣ Weightage (optional)
    if features.get("weightage"):
        w = features["weightage"]
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
