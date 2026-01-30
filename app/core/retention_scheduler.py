from datetime import date, datetime


DECAY_CONFIG = {
    "Easy": 7,
    "Medium": 5,
    "Hard": 3
}


def apply_retention_decay(learner_state, today=None):
    """
    Marks topics for revision based on last studied date
    """

    if today is None:
        today = date.today()

    topic_states = learner_state.get("topic_states", {})

    for topic_id, state in topic_states.items():
        last = state.get("last_studied")
        complexity = state.get("complexity", "Medium")
        familiarity = state.get("familiarity", 0)

        if not last:
            continue

        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        gap = (today - last_date).days

        threshold = DECAY_CONFIG.get(complexity, 5)

        if gap >= threshold and familiarity < 0.75:
            state["revision_due"] = True

    return learner_state
