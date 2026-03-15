from app.database import users_collection
from bson import ObjectId


def get_user_profile(user_id: str) -> dict:
    """
    Load user profile from MongoDB.
    Returns relevant fields for plan personalization.
    """
    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        return _default_profile()

    return {
        "study_preference": user.get("study_preference", "Flexible"),
        "year": user.get("year", 2),
        "degree": user.get("degree", "B.Tech"),
        "branch": user.get("branch", "")
    }


def _default_profile() -> dict:
    return {
        "study_preference": "Flexible",
        "year": 2,
        "degree": "B.Tech",
        "branch": ""
    }


def get_topic_order_preference(study_preference: str) -> str:
    """
    Returns topic ordering strategy based on study preference.

    Morning → harder topics first (brain is fresh)
    Night   → easier topics first (warm up before hard)
    Flexible → no change (priority engine decides)
    """
    mapping = {
        "Morning": "hard_first",
        "Night": "easy_first",
        "Flexible": "priority"
    }
    return mapping.get(study_preference, "priority")


def get_year_pace_multiplier(year: int) -> float:
    """
    Returns a time multiplier based on academic year.

    Year 1-2 → slower pace → more time per topic (multiplier > 1)
    Year 3-4 → faster pace → less time per topic (multiplier < 1)
    """
    if year <= 2:
        return 1.2    # 20% more time per topic
    else:
        return 0.9    # 10% less time per topic