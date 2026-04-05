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

    self_rated_count = sum(
        1 for s in states if s.get("self_rated", False)
    )
    self_rated_ratio = self_rated_count / len(states)

    confidence = (avg_fam * 0.6 + avg_ret * 0.4)

    if self_rated_ratio > 0.5:
        confidence *= (1 - self_rated_ratio * 0.3)

    return round(confidence, 3)


# -------------------------------------------------
# Sort candidates by topic order preference
# -------------------------------------------------
def _sort_candidates(candidates, remaining_hours, topic_order):
    """
    topic_order:
        "hard_first"  → Morning users: sort Hard → Medium → Easy
        "easy_first"  → Night users:   sort Easy → Medium → Hard
        "priority"    → Flexible:      sort by priority score (default)
    """

    if topic_order == "hard_first":
        candidates.sort(
            key=lambda t: (
                -COMPLEXITY_ORDER.get(t["complexity"], 2),
                -t["priority"]
            )
        )

    elif topic_order == "easy_first":
        candidates.sort(
            key=lambda t: (
                COMPLEXITY_ORDER.get(t["complexity"], 2),
                -t["priority"]
            )
        )

    else:
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
        year_pace_multiplier: float — 1.2 for Year 1-2, 0.9 for Year 3-4
    """

    learning_speed = learner_state.get("learning_speed", 1.0)
    consistency = learner_state.get("consistency", 1.0)

    raw_effective = hours_per_day * learning_speed
    consistency_factor = max(0.8, consistency)
    effective_daily_hours = round(
        max(1.0, raw_effective * consistency_factor),
        2
    )

    # -------------------------------------------------------
    # FIX: Cap estimated_hours per topic so no single topic
    # dominates the whole plan. A topic should take at most
    # 20% of the total available study time across the plan.
    # Also apply a hard cap of 6 hours total per topic.
    # -------------------------------------------------------
    total_plan_hours = effective_daily_hours * deadline_days
    per_topic_cap = min(
        6.0,
        max(1.5, total_plan_hours * 0.15)   # at most 15% of plan per topic
    )

    # Apply year pace multiplier AND cap to estimated hours
    remaining_hours = {}
    for t in topics:
        raw = t["estimated_hours"] * year_pace_multiplier / max(0.5, learning_speed)

        # Familiarity discount: if user already knows this topic, reduce hours
        state = learner_state.get("topic_states", {}).get(t["topic"], {})
        familiarity = state.get("familiarity", 0.0)
        familiarity_discount = max(0.3, 1.0 - familiarity * 0.7)

        adjusted = raw * familiarity_discount
        remaining_hours[t["topic"]] = round(min(adjusted, per_topic_cap), 2)

    plan = defaultdict(list)
    total_days = deadline_days

    # -------------------------------------------------------
    # Consecutive days cap: reduced to 1 to force topic variety
    # each day. A topic can only appear on consecutive days
    # when there are very few topics left.
    # -------------------------------------------------------
    num_topics = len([t for t in topics if remaining_hours.get(t["topic"], 0) > 0])
    # If many topics: max 1 consecutive day. If few: allow 2.
    MAX_CONSECUTIVE_DAYS = 1 if num_topics > 5 else 2
    MAX_DAYS_PER_TOPIC_TOTAL = max(5, deadline_days // max(1, num_topics) + 2)

    consecutive_days = {}
    total_days_used = {}

    deadline_pressure = max(0.1, 1 / max(5, deadline_days))
    early_phase_days = math.ceil(total_days * 0.4)

    fatigue_counter = 0

    for day in range(1, total_days + 1):

        remaining_day_hours = effective_daily_hours

        if fatigue_counter >= 3:
            remaining_day_hours = round(remaining_day_hours * 0.7, 2)
            fatigue_counter = 0
        else:
            fatigue_counter += 1

        if day <= early_phase_days:
            max_complexity = 2
        else:
            max_complexity = 3

        if topic_order == "hard_first":
            max_complexity = 3

        topics_scheduled_today = set()

        candidates = []
        for t in topics:
            topic_name = t["topic"]

            if remaining_hours.get(topic_name, 0) <= 0:
                continue

            if consecutive_days.get(topic_name, 0) >= MAX_CONSECUTIVE_DAYS:
                continue

            if total_days_used.get(topic_name, 0) >= MAX_DAYS_PER_TOPIC_TOTAL:
                remaining_hours[topic_name] = 0
                continue

            t_copy = t.copy()
            t_copy["priority"] = compute_priority(
                t, learner_state, deadline_pressure
            )
            candidates.append(t_copy)

        candidates = _sort_candidates(candidates, remaining_hours, topic_order)

        # -----------------------------
        # Study Allocation
        # Aim to fit 2-3 different topics per day
        # by limiting each topic to ~40% of the day's hours
        # -----------------------------
        topics_added_today = 0
        MAX_TOPICS_PER_DAY = max(2, min(4, num_topics))

        for topic in candidates:

            if remaining_day_hours <= 0.1:
                break

            if topics_added_today >= MAX_TOPICS_PER_DAY:
                break

            topic_name = topic["topic"]
            topic_complexity = COMPLEXITY_ORDER[topic["complexity"]]

            if topic_complexity > max_complexity:
                continue

            available = remaining_hours.get(topic_name, 0)
            if available <= 0:
                continue

            # Each topic gets at most 50% of daily hours (to allow variety)
            # and at most 2 hours per session
            daily_topic_cap = min(
                2.0,
                remaining_day_hours * 0.6,
                available
            )

            max_per_session = min(daily_topic_cap, remaining_day_hours)

            if max_per_session < 0.25:
                if available <= 0.25:
                    allocated = round(available, 2)
                    remaining_hours[topic_name] = 0
                else:
                    continue
            else:
                allocated = round(max_per_session, 2)

            if allocated <= 0:
                continue

            plan[day].append({
                "type": "study",
                "topic": topic_name,
                "hours": allocated,
                "complexity": topic["complexity"]
            })

            remaining_hours[topic_name] = round(
                remaining_hours[topic_name] - allocated, 2
            )
            remaining_day_hours = round(remaining_day_hours - allocated, 2)

            topics_scheduled_today.add(topic_name)
            topics_added_today += 1

            total_days_used[topic_name] = total_days_used.get(topic_name, 0) + 1

        # Update consecutive_days correctly
        for t in topics:
            topic_name = t["topic"]
            if topic_name in topics_scheduled_today:
                consecutive_days[topic_name] = consecutive_days.get(topic_name, 0) + 1
            else:
                consecutive_days[topic_name] = 0

        # -----------------------------
        # Revision Allocation
        # -----------------------------
        revision_candidates = [
            (topic_name, state)
            for topic_name, state in learner_state.get("topic_states", {}).items()
            if state.get("revision_due", False)
        ]

        revision_candidates.sort(key=lambda x: x[1].get("retention", 1.0))

        if revision_candidates and remaining_day_hours >= 0.25:
            revision_budget = round(
                min(remaining_day_hours * 0.5, 0.5),
                2
            )

            topic_name = revision_candidates[0][0]
            plan[day].append({
                "type": "revision",
                "topic": topic_name,
                "hours": revision_budget
            })
            remaining_day_hours = round(remaining_day_hours - revision_budget, 2)

        # -----------------------------
        # Micro Test Slot
        # -----------------------------
        consistency = learner_state.get("consistency", 1.0)
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
        "profile_used": {
            "topic_order": topic_order,
            "year_pace_multiplier": year_pace_multiplier
        }
    }