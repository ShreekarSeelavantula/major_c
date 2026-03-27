import random


def sample_initial_unit_topics(structured_syllabus, n=20):
    """
    Select topics only from FIRST UNIT for deep diagnostic.
    Returns up to n topic names.
    """
    if not structured_syllabus:
        return []

    first_unit = structured_syllabus[0]
    topics = [t["name"] for t in first_unit.get("topics", [])]

    if not topics:
        return []

    return random.sample(topics, min(n, len(topics)))


def sample_micro_topics(structured_syllabus, learner_state, n=10):
    """
    ⭐ NEW: Unit-aware micro test sampling.

    Priority order:
    1. Topics from the NEXT self-rated unit (replace approximate with real)
    2. Weak topics from already-tested units (familiarity < 0.5)
    3. Random fallback from any unit

    Returns list of topic names.
    """
    topic_states = learner_state.get("topic_states", {})
    tested_units = set(learner_state.get("tested_units", []))

    # ---------------------------------------------------
    # Find the next self-rated unit (lowest unit number
    # that has NOT been properly tested yet)
    # ---------------------------------------------------
    next_unit = None
    next_unit_topics = []

    for unit in structured_syllabus:
        unit_num = unit.get("unit_number", 1)

        # Unit-1 was already tested in initial diagnostic — skip
        if unit_num == 1:
            continue

        # Already properly tested — skip
        if unit_num in tested_units:
            continue

        # This is the next unit to properly test
        next_unit = unit_num
        next_unit_topics = [t["name"] for t in unit.get("topics", [])]
        break

    # ---------------------------------------------------
    # If there's a self-rated unit to test, sample from it
    # ---------------------------------------------------
    if next_unit_topics:
        sampled = random.sample(next_unit_topics, min(n, len(next_unit_topics)))
        return sampled, next_unit   # ⭐ return unit number too

    # ---------------------------------------------------
    # All units tested — fall back to weak topics
    # ---------------------------------------------------
    weak_topics = [
        topic for topic, state in topic_states.items()
        if state.get("familiarity", 0) < 0.5
        and not state.get("self_rated", False)
    ]

    if len(weak_topics) >= n:
        return random.sample(weak_topics, n), None

    # ---------------------------------------------------
    # Final fallback — random from all topics
    # ---------------------------------------------------
    all_topics = [
        t["name"]
        for unit in structured_syllabus
        for t in unit.get("topics", [])
    ]

    if not all_topics:
        return [], None

    return random.sample(all_topics, min(n, len(all_topics))), None


def all_units_tested(structured_syllabus, learner_state):
    """
    Returns True if every unit (except Unit-1 which was
    tested in the initial diagnostic) has been properly
    tested via micro tests.
    """
    tested_units = set(learner_state.get("tested_units", []))

    for unit in structured_syllabus:
        unit_num = unit.get("unit_number", 1)
        if unit_num == 1:
            continue   # Unit-1 always tested in initial diagnostic
        if unit_num not in tested_units:
            return False

    return True