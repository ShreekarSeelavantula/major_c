from collections import defaultdict
import math

COMPLEXITY_ORDER = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}


def generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day,
    deadline_days
):
    """
    topics: output from syllabus_pipeline
    learner_state: learner model snapshot
    hours_per_day: daily available study hours
    deadline_days: total available days
    """

    # --- Track remaining hours per topic ---
    remaining_hours = {
        t["topic"]: t["estimated_hours"] for t in topics
    }

    plan = defaultdict(list)

    total_days = deadline_days
    early_phase_days = math.ceil(total_days * 0.4)

    for day in range(1, total_days + 1):
        remaining_day_hours = hours_per_day

        # Phase-based complexity allowance
        if day <= early_phase_days:
            max_complexity = 2  # Easy + Medium
        else:
            max_complexity = 3  # All

        # --- Build daily candidate pool ---
        candidates = [
            t for t in topics
            if remaining_hours[t["topic"]] > 0
        ]

        # Sort daily candidates
        candidates.sort(
            key=lambda t: (
                COMPLEXITY_ORDER[t["complexity"]],
                remaining_hours[t["topic"]]
            )
        )

        # --- Allocate study time ---
        for topic in candidates:
            if remaining_day_hours <= 0:
                break

            topic_name = topic["topic"]
            topic_complexity = COMPLEXITY_ORDER[topic["complexity"]]

            # Skip hard topics in early phase unless necessary
            if topic_complexity > max_complexity:
                continue

            available = remaining_hours[topic_name]

            if available <= 0:
                continue

            # Partial allocation allowed
            allocated = min(available, remaining_day_hours)

            plan[day].append({
                "type": "study",
                "topic": topic_name,
                "hours": round(allocated, 2),
                "complexity": topic["complexity"]
            })

            remaining_hours[topic_name] -= allocated
            remaining_day_hours -= allocated

        # --- Revision slot ---
        if day > 1:
            revision_time = round(min(1, hours_per_day * 0.2), 2)
            plan[day].append({
                "type": "revision",
                "hours": revision_time
            })

        # --- Micro familiarity test ---
        plan[day].append({
            "type": "micro_test",
            "questions": 5
        })

    return dict(plan)
