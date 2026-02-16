from datetime import datetime
from bson import ObjectId

from app.storage.learner_store import (
    get_learner_state,
    create_learner_state
)
from app.storage.plan_store import save_plan

from app.core.learner_initializer import initialize_learner_state
from app.core.adaptive_plan_generator import generate_adaptive_plan
from app.core.retention_scheduler import apply_retention_decay


def build_adaptive_plan(
    user_id: str,
    structured_syllabus: list,
    hours_per_day: float,
    deadline_days: int
):
    """
    Central coordinator for adaptive plan generation

    Steps:
    1. Load or initialize learner state
    2. Convert structured syllabus to topic-level input
    3. Apply retention decay
    4. Generate adaptive plan
    5. Persist plan
    """

    user_obj_id = ObjectId(user_id)

    # -------------------------------------------------
    # 1️⃣ Load or Initialize Learner State
    # -------------------------------------------------
    learner_state = get_learner_state(user_obj_id)

    if learner_state is None:

        topics_for_init = []

        for unit in structured_syllabus:
            for topic in unit.get("topics", []):
                topics_for_init.append({
                    "topic": topic["name"],
                    "estimated_hours": topic["estimated_hours"],
                    "complexity": topic["complexity"]
                })

        topic_states = initialize_learner_state(topics_for_init)

        # Wrap into full learner_state structure
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
                        t["complexity"]
                        for t in topics_for_init
                        if t["topic"] == topic_id
                    )
                }
                for topic_id, state in topic_states.items()
            },
            "learning_speed": 1.0,
            "consistency": 1.0,
            "history": []
        }

        create_learner_state(
            user_id=user_obj_id,
            learner_state=learner_state
        )

    # -------------------------------------------------
    # 2️⃣ Convert Structured Syllabus → Topic List
    # -------------------------------------------------
    topics = []

    for unit in structured_syllabus:
        for topic in unit.get("topics", []):
            topics.append({
                "topic": topic["name"],
                "estimated_hours": topic["estimated_hours"],
                "complexity": topic["complexity"]
            })

    if not topics:
        raise ValueError("No topics extracted from structured syllabus")

    # -------------------------------------------------
    # 3️⃣ Apply Retention Decay BEFORE Planning
    # -------------------------------------------------
    learner_state = apply_retention_decay(learner_state)

    # -------------------------------------------------
    # 4️⃣ Generate Adaptive Plan
    # -------------------------------------------------
    plan = generate_adaptive_plan(
        topics=topics,
        learner_state=learner_state,
        hours_per_day=hours_per_day,
        deadline_days=deadline_days
    )

    # -------------------------------------------------
    # 5️⃣ Persist Plan
    # -------------------------------------------------
    plan_id = save_plan(
        user_id=user_obj_id,
        plan=plan,
        metadata={
            "hours_per_day": hours_per_day,
            "deadline_days": deadline_days,
            "generated_at": datetime.utcnow()
        }
    )

    # -------------------------------------------------
    # 6️⃣ Return Response
    # -------------------------------------------------
    return {
        "plan_id": str(plan_id),
        "plan": plan
    }
