from collections import defaultdict
import math


COMPLEXITY_ORDER = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}


def compute_priority(topic, learner_state):
    """
    Deterministic Learner-Aware Priority
    Higher value = scheduled earlier
    """

    topic_name = topic["topic"]
    state = learner_state.get("topic_states", {}).get(topic_name, {})

    familiarity = state.get("familiarity", 0.0)
    confidence = state.get("confidence", 0.0)
    retention = state.get("retention", 1.0)
    revision_due = state.get("revision_due", False)

    normalized_complexity = COMPLEXITY_ORDER.get(
        topic["complexity"], 2
    ) / 3.0

    priority = (
        0.3 * normalized_complexity +
        0.3 * (1 - familiarity) +
        0.2 * (1 - retention) +
        0.2 * (1 if revision_due else 0)
    )

    return round(priority, 4)


def generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day,
    deadline_days
):
    """
    Deterministic Adaptive Plan Generator
    """

    learning_speed = learner_state.get("learning_speed", 1.0)
    consistency = learner_state.get("consistency", 1.0)

    effective_daily_hours = round(
        hours_per_day * learning_speed * consistency,
        2
    )

    # Adjust topic hours using learning speed
    remaining_hours = {
        t["topic"]: round(
            t["estimated_hours"] / max(0.5, learning_speed),
            2
        )
        for t in topics
    }

    plan = defaultdict(list)
    total_days = deadline_days

    early_phase_days = math.ceil(total_days * 0.4)

    for day in range(1, total_days + 1):

        remaining_day_hours = effective_daily_hours

        if day <= early_phase_days:
            max_complexity = 2
        else:
            max_complexity = 3

        # Build candidate pool
        candidates = []
        for t in topics:
            if remaining_hours[t["topic"]] > 0:
                t_copy = t.copy()
                t_copy["priority"] = compute_priority(t, learner_state)
                candidates.append(t_copy)

        candidates.sort(
            key=lambda t: (
                -t["priority"],
                COMPLEXITY_ORDER[t["complexity"]],
                remaining_hours[t["topic"]]
            )
        )

        # Allocate Study
        for topic in candidates:

            if remaining_day_hours <= 0:
                break

            topic_name = topic["topic"]
            topic_complexity = COMPLEXITY_ORDER[topic["complexity"]]

            if topic_complexity > max_complexity:
                continue

            available = remaining_hours[topic_name]
            if available <= 0:
                continue

            allocated = min(
                available,
                remaining_day_hours,
                max(0.5, available * 0.4)
            )

            allocated = round(allocated, 2)

            if allocated <= 0:
                continue


            plan[day].append({
                "type": "study",
                "topic": topic_name,
                "hours": allocated,
                "complexity": topic["complexity"]
            })

            remaining_hours[topic_name] -= allocated
            remaining_day_hours -= allocated

        # Revision slot
        # -----------------------------------------
        # Revision Allocation (Balanced Model A)
        # -----------------------------------------

        revision_candidates = [
            topic_name
            for topic_name, state in learner_state.get("topic_states", {}).items()
            if state.get("revision_due", False)
        ]

        if revision_candidates:

            revision_budget = round(effective_daily_hours * 0.1, 2)

            if remaining_day_hours >= revision_budget:

                topic_name = revision_candidates[0]

                plan[day].append({
                    "type": "revision",
                    "topic": topic_name,
                    "hours": revision_budget
                })

                remaining_day_hours -= revision_budget


        # Micro test
        base_questions = 5

        if consistency < 0.7:
            base_questions = 3
        elif learning_speed > 1.1:
            base_questions = 7

        plan[day].append({
            "type": "micro_test",
            "questions": base_questions
        })

    return dict(plan)
