from datetime import datetime, date
from copy import deepcopy
import math


def update_learner_state(
    learner_state,
    daily_report,
    today=None
):
    """
    learner_state: current learner snapshot (from MongoDB)
    daily_report: actual learner behavior for the day
    today: date (optional)
    """

    if today is None:
        today = datetime.utcnow()

    updated_state = deepcopy(learner_state)

    topic_states = updated_state.setdefault("topic_states", {})
    updated_state.setdefault("learning_speed", 1.0)
    updated_state.setdefault("consistency", 1.0)
    updated_state.setdefault("history", [])

    # --------------------------------------------------
    # 1️⃣ STUDY SESSIONS → familiarity + retention reset
    # --------------------------------------------------
    for session in daily_report.get("study_sessions", []):
        topic_id = session["topic_id"]
        time_spent = session["hours"]

        topic = topic_states.setdefault(topic_id, {
            "familiarity": 0.0,
            "confidence": 0.0,
            "retention": 1.0,
            "attempts": 0,
            "last_seen": None
        })

        # Familiarity gain (slow, bounded)
        gain = min(0.15, time_spent * 0.1)
        topic["familiarity"] = min(1.0, topic["familiarity"] + gain)

        # Confidence grows slower than familiarity
        topic["confidence"] = min(
            topic["confidence"] + 0.03,
            topic["familiarity"]
        )

        topic["retention"] = 1.0
        topic["attempts"] += 1
        topic["last_seen"] = today

    # --------------------------------------------------
    # 2️⃣ MICRO TESTS → correction signal
    # --------------------------------------------------
    for test in daily_report.get("micro_tests", []):
        topic_id = test["topic_id"]
        score = test["score"]  # 0–1

        topic = topic_states.setdefault(topic_id, {
            "familiarity": 0.0,
            "confidence": 0.0,
            "retention": 1.0,
            "attempts": 0,
            "last_seen": None
        })

        delta = (score - 0.5) * 0.15
        topic["familiarity"] = max(
            0.0,
            min(1.0, topic["familiarity"] + delta)
        )

        topic["confidence"] = min(
            topic["confidence"] + 0.05,
            topic["familiarity"]
        )

        topic["attempts"] += 1
        topic["last_seen"] = today

    # --------------------------------------------------
    # 3️⃣ RETENTION DECAY (forgetting curve)
    # --------------------------------------------------
    for topic in topic_states.values():
        if topic["last_seen"]:
            days_passed = (today - topic["last_seen"]).days
            topic["retention"] *= math.exp(-0.08 * days_passed)
            topic["retention"] = round(max(0.0, topic["retention"]), 3)

    # --------------------------------------------------
    # 4️⃣ LEARNING SPEED UPDATE
    # --------------------------------------------------
    expected = daily_report.get("expected_hours", 0)
    actual = daily_report.get("actual_hours", 0)

    if expected > 0:
        ratio = actual / expected
        updated_state["learning_speed"] = round(
            0.8 * updated_state["learning_speed"] + 0.2 * ratio,
            2
        )

    # --------------------------------------------------
    # 5️⃣ CONSISTENCY SIGNAL
    # --------------------------------------------------
    if actual < expected * 0.5:
        updated_state["consistency"] = max(
            0.5, updated_state["consistency"] - 0.05
        )
    else:
        updated_state["consistency"] = min(
            1.0, updated_state["consistency"] + 0.02
        )

    # --------------------------------------------------
    # 6️⃣ HISTORY LOG (immutable)
    # --------------------------------------------------
    updated_state["history"].append({
        "date": today.date().isoformat(),
        "actual_hours": actual,
        "expected_hours": expected
    })

    return updated_state
