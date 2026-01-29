from datetime import datetime
from math import exp
from app.models.learner_state import LearnerTopicState


def apply_retention_decay(
    topic_state: LearnerTopicState,
    current_time: datetime | None = None
) -> LearnerTopicState:
    """
    Applies forgetting curve decay to a topic's retention score
    """

    if topic_state.last_studied is None:
        return topic_state

    current_time = current_time or datetime.utcnow()

    days_passed = (current_time - topic_state.last_studied).days

    if days_passed <= 0:
        return topic_state

    # ---------- Forgetting Curve ----------
    # λ controls decay speed (tunable)
    decay_rate = 0.08

    decay_factor = exp(-decay_rate * days_passed)

    topic_state.retention_score *= decay_factor
    topic_state.retention_score = round(
        max(topic_state.retention_score, 0.0),
        2
    )

    # ---------- Revision Trigger ----------
    topic_state.revision_due = topic_state.retention_score < 0.4

    return topic_state
