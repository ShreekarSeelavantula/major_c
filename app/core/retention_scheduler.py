from datetime import date, datetime


DECAY_CONFIG = {
    "Easy": 7,
    "Medium": 5,
    "Hard": 3
}


def apply_retention_decay(learner_state, today=None):
    """
    Marks topics for revision based on:
    1. Time gap since last study
    2. Retention score (forgetting risk)
    """

    if today is None:
        today = date.today()

    topic_states = learner_state.get("topic_states", {})

    for topic_id, state in topic_states.items():

        last = state.get("last_studied")
        complexity = state.get("complexity", "Medium")
        familiarity = state.get("familiarity", 0.0)
        retention = state.get("retention", 1.0)

        if not last:
            state["revision_due"] = False
            continue

        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        gap = (today - last_date).days

        threshold = DECAY_CONFIG.get(complexity, 5)

        # 🔥 Improved Logic
        if (
            (gap >= threshold and familiarity < 0.75)
            or retention < 0.6
        ):
            state["revision_due"] = True
        else:
            state["revision_due"] = False

    return learner_state
