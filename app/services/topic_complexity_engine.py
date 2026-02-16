import re


# -------------------------------
# Bloom's Taxonomy Verb Mapping
# -------------------------------

BLOOM_VERB_SCORES = {
    "define": 1,
    "list": 1,
    "state": 1,

    "explain": 2,
    "describe": 2,
    "summarize": 2,

    "apply": 3,
    "implement": 3,
    "solve": 3,
    "design": 3,

    "analyze": 4,
    "optimize": 4,
    "evaluate": 4,
    "compare": 4
}


def calculate_subtopic_score(subtopics):
    count = len(subtopics)

    if count <= 2:
        return 1
    elif count <= 4:
        return 2
    else:
        return 3


def calculate_verb_score(topic_title):
    topic_title = topic_title.lower()

    for verb, score in BLOOM_VERB_SCORES.items():
        if verb in topic_title:
            return score

    # default if no verb found
    return 2


def calculate_concept_density_score(topic_title):
    # count commas as proxy for multiple concepts
    concepts = re.split(r",|and", topic_title)
    count = len(concepts)

    if count <= 2:
        return 1
    elif count <= 4:
        return 2
    else:
        return 3


def calculate_dependency_score(topic_index):
    """
    Simple rule:
    First topic → independent
    Later topics → assume dependency grows
    """

    if topic_index == 0:
        return 1
    elif topic_index <= 2:
        return 2
    else:
        return 3


def classify_difficulty(total_score):
    if total_score <= 6:
        return "Easy"
    elif total_score <= 10:
        return "Medium"
    else:
        return "Hard"


def evaluate_topic(topic_title, subtopics, topic_index):
    subtopic_score = calculate_subtopic_score(subtopics)
    verb_score = calculate_verb_score(topic_title)
    density_score = calculate_concept_density_score(topic_title)
    dependency_score = calculate_dependency_score(topic_index)

    total_score = (
        subtopic_score
        + verb_score
        + density_score
        + dependency_score
    )

    difficulty = classify_difficulty(total_score)

    return {
        "subtopic_score": subtopic_score,
        "verb_score": verb_score,
        "density_score": density_score,
        "dependency_score": dependency_score,
        "total_score": total_score,
        "difficulty": difficulty
    }
