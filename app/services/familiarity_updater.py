import math
import time


# -----------------------------
# Memory Model Constants
# -----------------------------
RETENTION_DECAY_RATE = 0.15      # forgetting speed
SMOOTHING_ALPHA = 0.6            # learning smoothing


def _apply_retention_decay(topic_state):
    """
    Apply exponential forgetting curve
    """

    last = topic_state.get("last_updated")

    if not last:
        return topic_state

    days_passed = (time.time() - last) / 86400

    decay_factor = math.exp(-RETENTION_DECAY_RATE * days_passed)

    topic_state["retention"] = round(
        topic_state.get("retention", 1.0) * decay_factor,
        3
    )

    # revision trigger
    if topic_state["retention"] < 0.6:
        topic_state["revision_due"] = True

    return topic_state


def update_familiarity(learner_state, topic_scores):
    """
    Intelligent Familiarity Updater
    - Smooth learning
    - Forgetting curve
    - Confidence tracking
    - Revision scheduling
    """

    if "topic_states" not in learner_state:
        learner_state["topic_states"] = {}

    for topic, score in topic_scores.items():

        topic_state = learner_state["topic_states"].get(topic)

        # ---------------------------------
        # NEW TOPIC INITIALIZATION
        # ---------------------------------
        if not topic_state:
            learner_state["topic_states"][topic] = {
                "familiarity": round(score, 3),
                "confidence": round(score, 3),
                "retention": 1.0,
                "attempts": 1,
                "revision_due": False,
                "last_updated": time.time()
            }
            continue

        # ---------------------------------
        # Apply retention decay
        # ---------------------------------
        topic_state = _apply_retention_decay(topic_state)

        # ---------------------------------
        # Smooth familiarity learning
        # ---------------------------------
        old_familiarity = topic_state.get("familiarity", 0.0)

        new_familiarity = (
            SMOOTHING_ALPHA * score +
            (1 - SMOOTHING_ALPHA) * old_familiarity
        )

        topic_state["familiarity"] = round(new_familiarity, 3)

        # ---------------------------------
        # Confidence grows slower
        # ---------------------------------
        topic_state["confidence"] = round(
            topic_state.get("confidence", 0.0) * 0.7 +
            score * 0.3,
            3
        )

        # ---------------------------------
        # Attempts counter
        # ---------------------------------
        topic_state["attempts"] = topic_state.get("attempts", 0) + 1

        topic_state["last_updated"] = time.time()

        # ---------------------------------
        # Revision scheduling logic
        # ---------------------------------
        if topic_state["familiarity"] < 0.5:
            topic_state["revision_due"] = True
        else:
            topic_state["revision_due"] = False

    return learner_state