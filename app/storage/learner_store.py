import json
import os
from datetime import datetime

BASE_PATH = "data/learners"


def _ensure_dir():
    os.makedirs(BASE_PATH, exist_ok=True)


# --------------------------------------------------
# SAVE
# --------------------------------------------------
def save_learner_state(user_id: str, learner_state: dict):
    """
    Persist learner state to JSON file.
    Called after every familiarity test + daily update.
    """
    _ensure_dir()
    path = os.path.join(BASE_PATH, f"{user_id}.json")

    # datetime objects are not JSON serializable — convert to string
    def _serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(path, "w") as f:
        json.dump(learner_state, f, indent=2, default=_serialize)


# --------------------------------------------------
# LOAD
# --------------------------------------------------
def load_learner_state(user_id: str) -> dict | None:
    """
    Load learner state from JSON file.
    Returns None if no state exists yet.
    """
    path = os.path.join(BASE_PATH, f"{user_id}.json")

    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        return json.load(f)


# --------------------------------------------------
# GET  (alias used by plan_orchestrator)
# --------------------------------------------------
def get_learner_state(user_id) -> dict | None:
    """
    Alias for load_learner_state.
    Accepts ObjectId or string user_id.
    """
    return load_learner_state(str(user_id))


# --------------------------------------------------
# CREATE  (used by plan_orchestrator on first visit)
# --------------------------------------------------
def create_learner_state(user_id, learner_state: dict):
    """
    Save a brand new learner state.
    Same as save but named clearly for first-time creation.
    """
    save_learner_state(str(user_id), learner_state)


# --------------------------------------------------
# UPDATE TOPIC STATES  (partial update helper)
# --------------------------------------------------
def update_topic_states(user_id: str, topic_scores: dict):
    """
    Load existing state, merge new topic scores, save back.
    Used after familiarity tests so we never overwrite
    unrelated topic states.
    """
    state = load_learner_state(user_id) or {"topic_states": {}}

    if "topic_states" not in state:
        state["topic_states"] = {}

    for topic, score in topic_scores.items():
        existing = state["topic_states"].get(topic, {})
        attempts = existing.get("attempts", 0)
        old_familiarity = existing.get("familiarity", 0.0)

        # Running mean update
        new_familiarity = (
            old_familiarity * attempts + score
        ) / (attempts + 1)

        state["topic_states"][topic] = {
            "familiarity": round(new_familiarity, 3),
            "confidence": round(new_familiarity, 3),
            "retention": existing.get("retention", 1.0),
            "attempts": attempts + 1,
            "revision_due": new_familiarity < 0.5,
            "last_updated": datetime.utcnow().isoformat()
        }

    save_learner_state(user_id, state)
    return state