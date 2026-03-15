from collections import defaultdict
import math


COMPLEXITY_ORDER = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}


# -------------------------------------------------
# Priority Engine (Upgraded)
# -------------------------------------------------
def compute_priority(topic, learner_state, deadline_pressure):

    topic_name = topic["topic"]
    state = learner_state.get("topic_states", {}).get(topic_name, {})

    familiarity = state.get("familiarity", 0.0)
    retention = state.get("retention", 1.0)
    revision_due = state.get("revision_due", False)

    normalized_complexity = COMPLEXITY_ORDER.get(
        topic["complexity"], 2
    ) / 3.0

    priority = (
        0.35 * normalized_complexity +
        0.30 * (1 - familiarity) +
        0.20 * (1 - retention) +
        0.15 * (1 if revision_due else 0)
    )

    # deadline pressure boost
    priority *= (1 + deadline_pressure)

    return round(priority, 4)


# -------------------------------------------------
# Plan Confidence Score
# -------------------------------------------------
def compute_plan_confidence(learner_state):

    states = learner_state.get("topic_states", {}).values()

    if not states:
        return 0.5

    avg_fam = sum(s.get("familiarity", 0.5) for s in states) / len(states)
    avg_ret = sum(s.get("retention", 1.0) for s in states) / len(states)

    return round((avg_fam * 0.6 + avg_ret * 0.4), 3)


# -------------------------------------------------
# Adaptive Planner
# -------------------------------------------------
def generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day,
    deadline_days
):

    learning_speed = learner_state.get("learning_speed", 1.0)
    consistency = learner_state.get("consistency", 1.0)

    effective_daily_hours = round(
        hours_per_day * learning_speed * consistency,
        2
    )

    remaining_hours = {
        t["topic"]: round(
            t["estimated_hours"] / max(0.5, learning_speed),
            2
        )
        for t in topics
    }

    plan = defaultdict(list)
    total_days = deadline_days

    # ---------------------------------------------
    # Deadline Pressure Model
    # ---------------------------------------------
    deadline_pressure = max(0.1, 1 / max(5, deadline_days))

    early_phase_days = math.ceil(total_days * 0.4)

    fatigue_counter = 0

    for day in range(1, total_days + 1):

        remaining_day_hours = effective_daily_hours

        if fatigue_counter >= 3:
            # burnout prevention day
            remaining_day_hours *= 0.6
            fatigue_counter = 0
        else:
            fatigue_counter += 1

        if day <= early_phase_days:
            max_complexity = 2
        else:
            max_complexity = 3

        candidates = []

        for t in topics:
            if remaining_hours[t["topic"]] > 0:
                t_copy = t.copy()
                t_copy["priority"] = compute_priority(
                    t,
                    learner_state,
                    deadline_pressure
                )
                candidates.append(t_copy)

        candidates.sort(
            key=lambda t: (
                -t["priority"],
                COMPLEXITY_ORDER[t["complexity"]],
                remaining_hours[t["topic"]]
            )
        )

        # -----------------------------
        # Study Allocation
        # -----------------------------
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
                max(0.5, available * 0.45)
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

        # -----------------------------
        # Revision Allocation
        # -----------------------------
        revision_candidates = [
            topic_name
            for topic_name, state in learner_state.get("topic_states", {}).items()
            if state.get("revision_due", False)
        ]

        if revision_candidates:

            revision_budget = round(effective_daily_hours * 0.12, 2)

            if remaining_day_hours >= revision_budget:

                topic_name = revision_candidates[0]

                plan[day].append({
                    "type": "revision",
                    "topic": topic_name,
                    "hours": revision_budget
                })

                remaining_day_hours -= revision_budget

        # -----------------------------
        # Micro Test Slot
        # -----------------------------
        base_questions = 5

        if consistency < 0.7:
            base_questions = 3
        elif learning_speed > 1.1:
            base_questions = 7

        plan[day].append({
            "type": "micro_test",
            "questions": base_questions
        })

    # ---------------------------------------------
    # Attach Plan Confidence
    # ---------------------------------------------
    confidence = compute_plan_confidence(learner_state)

    return {
        "schedule": dict(plan),
        "confidence": confidence
    }