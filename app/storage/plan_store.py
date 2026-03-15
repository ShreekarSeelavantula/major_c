import json
import os
from datetime import datetime
from bson import ObjectId

BASE_PATH = "data/plans"


def _ensure_dir():
    os.makedirs(BASE_PATH, exist_ok=True)


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# --------------------------------------------------
# SAVE  (returns plan_id)
# --------------------------------------------------
def save_plan(user_id, plan: dict, metadata: dict = None) -> str:
    """
    Save a study plan and return its plan_id.
    plan_id = user_id so one active plan per user for now.
    metadata: optional dict with hours_per_day, deadline_days, generated_at
    """
    _ensure_dir()

    plan_id = str(user_id)
    path = os.path.join(BASE_PATH, f"{plan_id}.json")

    document = {
        "plan_id": plan_id,
        "user_id": str(user_id),
        "plan": plan,
        "hours_per_day": (metadata or {}).get("hours_per_day"),
        "deadline_days": (metadata or {}).get("deadline_days"),
        "created_at": (metadata or {}).get(
            "generated_at", datetime.utcnow()
        )
    }

    with open(path, "w") as f:
        json.dump(document, f, indent=2, default=_serialize)

    return plan_id


# --------------------------------------------------
# GET BY PLAN ID
# --------------------------------------------------
def get_study_plan(plan_id: str, user_id: str) -> dict | None:
    """
    Load a plan by plan_id.
    Validates that it belongs to user_id.
    Returns None if not found or unauthorized.
    """
    path = os.path.join(BASE_PATH, f"{plan_id}.json")

    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        document = json.load(f)

    # ownership check
    if str(document.get("user_id")) != str(user_id):
        return None

    return document


# --------------------------------------------------
# LOAD BY USER ID  (latest plan for user)
# --------------------------------------------------
def load_plan(user_id: str) -> dict | None:
    """
    Load the current plan for a user.
    """
    return get_study_plan(str(user_id), str(user_id))