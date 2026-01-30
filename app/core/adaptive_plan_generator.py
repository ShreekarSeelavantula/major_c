from collections import defaultdict
import math


COMPLEXITY_ORDER = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}


def compute_priority(topic, learner_state):
    """
    Higher priority value = scheduled earlier
    Learner-aware priority computation
    """
    topic_name = topic["topic"]
    state = learner_state.get("topic_states", {}).get(topic_name, {})

    familiarity = state.get("familiarity", 0.0)
    confidence = state.get("confidence", 0.0)
    retention = state.get("retention", 1.0)
    revision_due = state.get("revision_due", False)

    priority = (
        (1 - familiarity) * 3.0          # weak topics first
        + (1 - confidence) * 2.0          # low certainty
        + (1 - retention) * 2.5           # decay risk
        + COMPLEXITY_ORDER[topic["complexity"]] * 0.5
        + (2.5 if revision_due else 0.0)  # forced revision
    )

    return round(priority, 2)


def generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day,
    deadline_days
):
    """
    Adaptive Plan Generator v2
    Learner-aware, retention-aware, empathetic pacing
    """

    # -----------------------------
    # Learner-level modifiers
    # -----------------------------
    learning_speed = learner_state.get("learning_speed", 1.0)
    consistency = learner_state.get("consistency", 1.0)

    effective_daily_hours = round(
        hours_per_day * learning_speed * consistency, 2
    )

    # -----------------------------
    # Track remaining hours per topic
    # -----------------------------
    remaining_hours = {
        t["topic"]: t["estimated_hours"] for t in topics
    }

    plan = defaultdict(list)

    total_days = deadline_days
    early_phase_days = math.ceil(total_days * 0.4)

    # -----------------------------
    # Day-wise scheduling
    # -----------------------------
    for day in range(1, total_days + 1):
        remaining_day_hours = effective_daily_hours

        # Phase-based complexity allowance
        if day <= early_phase_days:
            max_complexity = 2  # Easy + Medium
        else:
            max_complexity = 3  # All

        # -----------------------------
        # Build candidate pool
        # -----------------------------
        candidates = []
        for t in topics:
            if remaining_hours[t["topic"]] > 0:
                t_copy = t.copy()
                t_copy["priority"] = compute_priority(t, learner_state)
                candidates.append(t_copy)

        # Sort by priority (DESC = more urgent first)
        candidates.sort(
            key=lambda t: (
                -t["priority"],
                COMPLEXITY_ORDER[t["complexity"]],
                remaining_hours[t["topic"]]
            )
        )

        # -----------------------------
        # Allocate study time
        # -----------------------------
        for topic in candidates:
            if remaining_day_hours <= 0:
                break

            topic_name = topic["topic"]
            topic_complexity = COMPLEXITY_ORDER[topic["complexity"]]

            # Skip hard topics early unless unavoidable
            if topic_complexity > max_complexity:
                continue

            available = remaining_hours[topic_name]
            if available <= 0:
                continue

            allocated = min(
                available,
                remaining_day_hours,
                max(0.5, available * 0.4)  # avoid micro-fragmentation
            )

            allocated = round(allocated, 2)

            plan[day].append({
                "type": "study",
                "topic": topic_name,
                "hours": allocated,
                "complexity": topic["complexity"]
            })

            remaining_hours[topic_name] -= allocated
            remaining_day_hours -= allocated

        # -----------------------------
        # Revision slot (retention-aware)
        # -----------------------------
        for topic_name, state in learner_state.get("topic_states", {}).items():
            if (
                state.get("retention", 1.0) < 0.6
                and remaining_day_hours >= 0.3
            ):
                plan[day].append({
                    "type": "revision",
                    "topic": topic_name,
                    "hours": 0.3
                })
                remaining_day_hours -= 0.3
                break

        # -----------------------------
        # Adaptive micro familiarity test
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

    return dict(plan)
