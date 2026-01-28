# app/services/complexity_analyzer.py

# ---------------- Bloom's Verb Scores ----------------

BLOOMS_VERB_SCORES = {
    "define": 1,
    "list": 1,
    "identify": 1,

    "explain": 2,
    "describe": 2,
    "discuss": 2,

    "apply": 3,
    "implement": 3,
    "design": 3,

    "analyze": 4,
    "evaluate": 4,
    "optimize": 4
}


# ---------------- Factor Scorers ----------------

def score_subtopics(subtopic_count: int) -> int:
    if subtopic_count <= 2:
        return 1
    elif subtopic_count <= 4:
        return 2
    return 3


def score_verb(verb: str) -> int:
    return BLOOMS_VERB_SCORES.get(verb.lower(), 2)


def score_concept_density(concept_count: int) -> int:
    if concept_count <= 2:
        return 1
    elif concept_count <= 4:
        return 2
    return 3


def score_dependencies(dependency_level: int) -> int:
    if dependency_level == 0:
        return 1
    elif dependency_level == 1:
        return 2
    return 3


def score_weightage(weightage_percent: float | None) -> int:
    if weightage_percent is None:
        return 0
    if weightage_percent < 5:
        return 1
    elif weightage_percent <= 10:
        return 2
    return 3


# ---------------- Master Complexity Calculator ----------------

def calculate_topic_complexity(
    subtopic_count: int,
    verb: str,
    concept_count: int,
    dependency_level: int,
    weightage_percent: float | None = None
) -> dict:

    total_score = 0

    total_score += score_subtopics(subtopic_count)
    total_score += score_verb(verb)
    total_score += score_concept_density(concept_count)
    total_score += score_dependencies(dependency_level)
    total_score += score_weightage(weightage_percent)

    if total_score <= 6:
        complexity = "Easy"
    elif total_score <= 10:
        complexity = "Medium"
    else:
        complexity = "Hard"

    return {
        "score": total_score,
        "complexity": complexity
    }
