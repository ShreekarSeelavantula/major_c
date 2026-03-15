import random


def sample_initial_unit_topics(structured_syllabus, n=20):
    """
    Select topics only from FIRST UNIT for deep diagnostic
    """

    if not structured_syllabus:
        return []

    first_unit = structured_syllabus[0]

    topics = [t["name"] for t in first_unit.get("topics", [])]

    if not topics:
        return []

    return random.sample(
        topics,
        min(n, len(topics))
    )


def sample_micro_topics(structured_syllabus, learner_state, n=5):
    """
    Progressive weak-topic sampling
    """

    weak_topics = []

    topic_states = learner_state.get("topic_states", {})

    for topic, state in topic_states.items():
        if state.get("familiarity", 0) < 0.5:
            weak_topics.append(topic)

    if len(weak_topics) >= n:
        return random.sample(weak_topics, n)

    # fallback → random from all syllabus
    all_topics = []

    for unit in structured_syllabus:
        for topic in unit.get("topics", []):
            all_topics.append(topic["name"])

    if not all_topics:
        return []

    return random.sample(
        all_topics,
        min(n, len(all_topics))
    )