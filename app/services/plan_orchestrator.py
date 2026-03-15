from datetime import datetime
from bson import ObjectId

from app.storage.learner_store import (
    get_learner_state,
    create_learner_state,
    save_learner_state
)
from app.storage.plan_store import save_plan

from app.core.learner_initializer import initialize_learner_state
from app.core.adaptive_plan_generator import generate_adaptive_plan
from app.core.retention_scheduler import apply_retention_decay

# ⭐ NEW: profile reader
from app.services.user_profile import (
    get_user_profile,
    get_topic_order_preference,
    get_year_pace_multiplier
)


def build_adaptive_plan(
    user_id: str,
    structured_syllabus: list,
    hours_per_day: float,
    deadline_days: int
):
    """
    Central coordinator for adaptive plan generation.

    Steps:
    1. Convert structured syllabus → flat topic list
    2. Load existing learner state (has familiarity from tests)
       OR initialize fresh state if first time
    3. ⭐ Merge familiarity test scores into learner state
    4. Apply retention decay
    5. Generate adaptive plan
    6. Persist plan
    """

    user_id_str = str(user_id)

    # -------------------------------------------------
    # 1️⃣ Convert Structured Syllabus → Flat Topic List
    # -------------------------------------------------
    topics = []

    for unit in structured_syllabus:
        for topic in unit.get("topics", []):

            # ⭐ FIX: use "difficulty" string field, not "complexity" dict
            complexity = (
                topic.get("difficulty")
                or (
                    topic["complexity"]["difficulty"]
                    if isinstance(topic.get("complexity"), dict)
                    else topic.get("complexity", "Medium")
                )
            )

            topics.append({
                "topic": topic["name"],
                "complexity": complexity,
                "estimated_hours": topic["estimated_hours"]
            })

    if not topics:
        raise ValueError("No topics extracted from structured syllabus")

    # -------------------------------------------------
    # 2️⃣ Load Existing Learner State
    #    This already contains familiarity scores from
    #    any familiarity tests the user has taken
    # -------------------------------------------------
    learner_state = get_learner_state(user_id_str)

    if learner_state is None:

        # First time — initialize with familiarity = 0.0 for all topics
        topic_states_init = initialize_learner_state(topics)

        learner_state = {
            "topic_states": {
                topic_id: {
                    "familiarity": state.familiarity,
                    "confidence": state.confidence,
                    "retention": 1.0,
                    "attempts": state.attempts,
                    "last_studied": None,
                    "revision_due": False,
                    "complexity": next(
                        (t["complexity"] for t in topics if t["topic"] == topic_id),
                        "Medium"
                    )
                }
                for topic_id, state in topic_states_init.items()
            },
            "learning_speed": 1.0,
            "consistency": 1.0,
            "history": []
        }

        create_learner_state(user_id_str, learner_state)

    else:
        # ⭐ FIX: Ensure every topic in the syllabus exists in learner state.
        # New topics (not yet tested) get familiarity=0.0.
        # Already-tested topics KEEP their existing familiarity scores.
        topic_states = learner_state.setdefault("topic_states", {})

        for t in topics:
            topic_name = t["topic"]
            if topic_name not in topic_states:
                # Topic not yet tested — add with defaults
                topic_states[topic_name] = {
                    "familiarity": 0.0,
                    "confidence": 0.0,
                    "retention": 1.0,
                    "attempts": 0,
                    "last_studied": None,
                    "revision_due": False,
                    "complexity": t["complexity"]
                }

        # Ensure top-level keys exist
        learner_state.setdefault("learning_speed", 1.0)
        learner_state.setdefault("consistency", 1.0)
        learner_state.setdefault("history", [])

        # Save merged state back
        save_learner_state(user_id_str, learner_state)

    # -------------------------------------------------
    # 3️⃣ Apply Retention Decay BEFORE Planning
    # -------------------------------------------------
    learner_state = apply_retention_decay(learner_state)

    # -------------------------------------------------
    # 4️⃣ Load User Profile
    # ⭐ study_preference + year affect plan generation
    # -------------------------------------------------
    profile = get_user_profile(user_id_str)

    topic_order = get_topic_order_preference(
        profile.get("study_preference", "Flexible")
    )

    year_pace = get_year_pace_multiplier(
        profile.get("year", 2)
    )

    print(f"Profile loaded → preference={profile.get('study_preference')}, "
          f"year={profile.get('year')}, "
          f"topic_order={topic_order}, "
          f"year_pace={year_pace}")

    # -------------------------------------------------
    # 5️⃣ Generate Adaptive Plan
    #    Priority engine now uses real familiarity scores
    #    + profile-aware topic ordering and pacing
    # -------------------------------------------------
    plan = generate_adaptive_plan(
        topics=topics,
        learner_state=learner_state,
        hours_per_day=hours_per_day,
        deadline_days=deadline_days,
        topic_order=topic_order,
        year_pace_multiplier=year_pace
    )

    # -------------------------------------------------
    # 6️⃣ Persist Plan
    # -------------------------------------------------
    plan_id = save_plan(
        user_id=user_id_str,
        plan=plan,
        metadata={
            "hours_per_day": hours_per_day,
            "deadline_days": deadline_days,
            "generated_at": datetime.utcnow()
        }
    )

    # -------------------------------------------------
    # 7️⃣ Return Response
    # -------------------------------------------------
    return {
        "plan_id": str(plan_id),
        "plan": plan
    }