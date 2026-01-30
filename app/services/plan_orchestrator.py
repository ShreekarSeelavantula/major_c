from datetime import datetime
from bson import ObjectId

from app.storage.learner_store import (
    get_learner_state,
    create_learner_state
)
from app.storage.plan_store import save_plan

from app.core.learner_initializer import initialize_learner_state
from app.core.adaptive_plan_generator import generate_adaptive_plan


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
    3. Generate adaptive plan
    4. Persist plan in MongoDB
    5. Return plan metadata
    """

    user_obj_id = ObjectId(user_id)

    # -----------------------------
    # 1️⃣ Load or initialize learner
    # -----------------------------
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

        learner_state = initialize_learner_state(topics_for_init)

        create_learner_state(
            user_id=user_obj_id,
            learner_state=learner_state
        )

    # -----------------------------
    # 2️⃣ Convert syllabus → topics
    # -----------------------------
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

    # -----------------------------
    # 3️⃣ Generate adaptive plan
    # -----------------------------
    plan = generate_adaptive_plan(
        topics=topics,
        learner_state=learner_state,
        hours_per_day=hours_per_day,
        deadline_days=deadline_days
    )

    # -----------------------------
    # 4️⃣ Persist plan
    # -----------------------------
    plan_id = save_plan(
        user_id=user_obj_id,
        plan=plan,
        metadata={
            "hours_per_day": hours_per_day,
            "deadline_days": deadline_days,
            "generated_at": datetime.utcnow()
        }
    )

    # -----------------------------
    # 5️⃣ Return result
    # -----------------------------
    return {
        "plan_id": str(plan_id),
        "plan": plan
    }
