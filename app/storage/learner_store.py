import json
import os

BASE_PATH = "data/learners"


def _ensure_dir():
    os.makedirs(BASE_PATH, exist_ok=True)


def save_learner_state(user_id, learner_state):
    _ensure_dir()
    path = os.path.join(BASE_PATH, f"{user_id}.json")

    with open(path, "w") as f:
        json.dump(learner_state, f, indent=2)


def load_learner_state(user_id):
    path = os.path.join(BASE_PATH, f"{user_id}.json")

    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        return json.load(f)
