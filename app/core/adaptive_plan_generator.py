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
    topics: list of dicts from syllabus_pipeline
    learner_state: learner model snapshot
    hours_per_day: int or float
    deadline_days: int
    """

    # --- Step 1: sort topics (easy + short first) ---
    topics = sorted(
        topics,
        key=lambda t: (
            COMPLEXITY_ORDER[t["complexity"]],
            t["estimated_hours"]
        )
    )

    # Track remaining hours per topic
    remaining_topic_hours = {
        t["topic"]: t["estimated_hours"] for t in topics
    }

    plan = defaultdict(list)
    total_days = deadline_days
    early_phase_days = math.ceil(total_days * 0.4)

    topic_index = 0

    # --- Step 2: day-wise scheduling ---
    for day in range(1, total_days + 1):
        remaining_day_hours = hours_per_day

        # Decide difficulty exposure
        if day <= early_phase_days:
            max_complexity_allowed = 2  # Easy + Medium
        else:
            max_complexity_allowed = 3  # All

        # --- Step 3: fill the day ---
        while remaining_day_hours > 0 and topic_index < len(topics):
            topic = topics[topic_index]
            topic_name = topic["topic"]
            topic_complexity = COMPLEXITY_ORDER[topic["complexity"]]

            if topic_complexity > max_complexity_allowed:
                topic_index += 1
                continue

            remaining_hours = remaining_topic_hours[topic_name]

            if remaining_hours <= 0:
                topic_index += 1
                continue

            study_hours = min(remaining_hours, remaining_day_hours)

            plan[day].append({
                "type": "study",
                "topic": topic_name,
                "hours": study_hours,
                "complexity": topic["complexity"]
            })

            remaining_topic_hours[topic_name] -= study_hours
            remaining_day_hours -= study_hours

            if remaining_topic_hours[topic_name] <= 0:
                topic_index += 1

        # --- Step 4: revision slot ---
        if day > 1:
            plan[day].append({
                "type": "revision",
                "hours": min(1, hours_per_day * 0.2)
            })

        # --- Step 5: micro familiarity test ---
        plan[day].append({
            "type": "micro_test",
            "questions": 5
        })

    return dict(plan)
