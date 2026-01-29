from datetime import datetime
from app.models.learner_state import LearnerTopicState


def update_learner_topic_state(
    topic_state: LearnerTopicState,
    performance_score: float,
    time_spent_minutes: int,
    expected_time_minutes: int
) -> LearnerTopicState:
    """
    Updates learner topic state after a learning session
    """

    # ---------- Safety Guards ----------
    performance_score = max(0.0, min(1.0, performance_score))
    expected_time_minutes = max(expected_time_minutes, 1)

    # ---------- Familiarity Update ----------
    learning_rate = 0.15
    topic_state.familiarity += learning_rate * performance_score
    topic_state.familiarity = min(topic_state.familiarity, 1.0)

    # ---------- Learning Speed Update ----------
    speed_ratio = expected_time_minutes / max(time_spent_minutes, 1)
    topic_state.learning_speed = round(
        0.7 * topic_state.learning_speed + 0.3 * speed_ratio,
        2
    )

    # ---------- Confidence Update ----------
    topic_state.confidence = round(
        (topic_state.familiarity + performance_score) / 2,
        2
    )

    # ---------- Retention Update ----------
    retention_gain = 0.1 * performance_score
    topic_state.retention_score += retention_gain
    topic_state.retention_score = min(topic_state.retention_score, 1.0)

    # ---------- Revision Logic ----------
    topic_state.revision_due = topic_state.retention_score < 0.4

    # ---------- Meta Updates ----------
    topic_state.attempts += 1
    topic_state.last_studied = datetime.utcnow()

    return topic_state
