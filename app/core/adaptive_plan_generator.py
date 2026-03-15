from collections import defaultdict
import math


COMPLEXITY_ORDER = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3
}


# -------------------------------------------------
# Priority Engine
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

    priority *= (1 + deadline_pressure)

    return round(priority, 4)


# -------------------------------------------------
# Plan Confidence Score
# -------------------------------------------------
def compute_plan_confidence(learner_state):

    states = list(learner_state.get("topic_states", {}).values())

    if not states:
        return 0.5

    avg_fam = sum(s.get("familiarity", 0.5) for s in states) / len(states)
    avg_ret = sum(s.get("retention", 1.0) for s in states) / len(states)

    # ⭐ Lower confidence if many topics are self-rated only
    self_rated_count = sum(
        1 for s in states if s.get("self_rated", False)
    )
    self_rated_ratio = self_rated_count / len(states)

    confidence = (avg_fam * 0.6 + avg_ret * 0.4)

    # Penalize confidence if more than 50% topics are self-rated
    if self_rated_ratio > 0.5:
        confidence *= (1 - self_rated_ratio * 0.3)

    return round(confidence, 3)


# -------------------------------------------------
# Sort candidates by topic order preference
# ⭐ NEW: uses study_preference from user profile
# -------------------------------------------------
def _sort_candidates(candidates, remaining_hours, topic_order):
    """
    topic_order:
        "hard_first"  → Morning users: sort Hard → Medium → Easy
        "easy_first"  → Night users:   sort Easy → Medium → Hard
        "priority"    → Flexible:      sort by priority score (default)
    """

    if topic_order == "hard_first":
        # Hard topics first — brain is fresh in the morning
        candidates.sort(
            key=lambda t: (
                -COMPLEXITY_ORDER.get(t["complexity"], 2),
                -t["priority"]
            )
        )

    elif topic_order == "easy_first":
        # Easy topics first — warm up before tackling hard ones at night
        candidates.sort(
            key=lambda t: (
                COMPLEXITY_ORDER.get(t["complexity"], 2),
                -t["priority"]
            )
        )

    else:
        # Default: priority engine decides
        candidates.sort(
            key=lambda t: (
                -t["priority"],
                COMPLEXITY_ORDER[t["complexity"]],
                remaining_hours[t["topic"]]
            )
        )

    return candidates


# -------------------------------------------------
# Adaptive Planner
# ⭐ NEW params: topic_order, year_pace_multiplier
# -------------------------------------------------
def generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day,
    deadline_days,
    topic_order: str = "priority",
    year_pace_multiplier: float = 1.0
):
    """
    Args:
        topics:               list of {topic, complexity, estimated_hours}
        learner_state:        full learner state dict
        hours_per_day:        user's daily study hours
        deadline_days:        days until exam
        topic_order:          "hard_first" | "easy_first" | "priority"
                              derived from study_preference
        year_pace_multiplier: float from get_year_pace_multiplier()
                              1.2 for Year 1-2, 0.9 for Year 3-4
    """

    learning_speed = learner_state.get("learning_speed", 1.0)
    consistency = learner_state.get("consistency", 1.0)

    effective_daily_hours = round(
        hours_per_day * learning_speed * consistency,
        2
    )

    # ⭐ Apply year pace multiplier to estimated hours
    # Year 1-2 students get more time per topic
    # Year 3-4 students get less time per topic
    remaining_hours = {
        t["topic"]: round(
            t["estimated_hours"]
            * year_pace_multiplier
            / max(0.5, learning_speed),
            2
        )
        for t in topics
    }

    plan = defaultdict(list)
    total_days = deadline_days

    deadline_pressure = max(0.1, 1 / max(5, deadline_days))
    early_phase_days = math.ceil(total_days * 0.4)

    fatigue_counter = 0

    for day in range(1, total_days + 1):

        remaining_day_hours = effective_daily_hours

        if fatigue_counter >= 3:
            remaining_day_hours *= 0.6
            fatigue_counter = 0
        else:
            fatigue_counter += 1

        if day <= early_phase_days:
            max_complexity = 2
        else:
            max_complexity = 3

        # ⭐ Exception: if topic_order is hard_first,
        # allow Hard topics from Day 1 (morning users can handle it)
        if topic_order == "hard_first":
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

        # ⭐ Sort using profile-aware ordering
        candidates = _sort_candidates(
            candidates,
            remaining_hours,
            topic_order
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
        base_questions = 10

        if consistency < 0.7:
            base_questions = 5
        elif learning_speed > 1.1:
            base_questions = 10

        plan[day].append({
            "type": "micro_test",
            "questions": base_questions
        })

    confidence = compute_plan_confidence(learner_state)

    return {
        "schedule": dict(plan),
        "confidence": confidence,
        # ⭐ Store profile settings used so UI can show them
        "profile_used": {
            "topic_order": topic_order,
            "year_pace_multiplier": year_pace_multiplier
        }
    }