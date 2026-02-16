from datetime import datetime
from copy import deepcopy
import math


def update_learner_state(
    learner_state,
    daily_report,
    today=None
):

    if today is None:
        today = datetime.utcnow()

    updated_state = deepcopy(learner_state)

    topic_states = updated_state.setdefault("topic_states", {})
    updated_state.setdefault("learning_speed", 1.0)
    updated_state.setdefault("consistency", 1.0)
    updated_state.setdefault("history", [])

    # -----------------------------------
    # 1. STUDY SESSIONS
    # -----------------------------------
    for session in daily_report.get("study_sessions", []):
        topic_id = session["topic_id"]
        time_spent = session["hours"]

        topic = topic_states.setdefault(topic_id, {
            "familiarity": 0.0,
            "confidence": 0.0,
            "retention": 1.0,
            "attempts": 0,
            "last_studied": None,
            "revision_due": False
        })

        gain = min(0.15, time_spent * 0.1)
        topic["familiarity"] = min(1.0, topic["familiarity"] + gain)

        topic["confidence"] = min(
            topic["confidence"] + 0.03,
            topic["familiarity"]
        )

        topic["retention"] = 1.0
        topic["attempts"] += 1
        topic["last_studied"] = today.date().isoformat()
        topic["revision_due"] = False

    # -----------------------------------
    # 2. MICRO TESTS
    # -----------------------------------
    for test in daily_report.get("micro_tests", []):
        topic_id = test["topic_id"]
        score = test["score"]

        topic = topic_states.setdefault(topic_id, {
            "familiarity": 0.0,
            "confidence": 0.0,
            "retention": 1.0,
            "attempts": 0,
            "last_studied": None,
            "revision_due": False
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
        topic["last_studied"] = today.date().isoformat()

    # -----------------------------------
    # 3. RETENTION DECAY
    # -----------------------------------
    for topic in topic_states.values():
        if topic.get("last_studied"):
            last_date = datetime.strptime(
                topic["last_studied"],
                "%Y-%m-%d"
            )
            days_passed = (today - last_date).days

            topic["retention"] *= math.exp(-0.08 * days_passed)
            topic["retention"] = round(
                max(0.0, topic["retention"]),
                3
            )

    # -----------------------------------
    # 4. LEARNING SPEED UPDATE
    # -----------------------------------
    expected = daily_report.get("expected_hours", 0)
    actual = daily_report.get("actual_hours", 0)

    if expected > 0:
        ratio = actual / expected
        updated_state["learning_speed"] = round(
            0.8 * updated_state["learning_speed"] + 0.2 * ratio,
            2
        )

    # -----------------------------------
    # 5. CONSISTENCY UPDATE
    # -----------------------------------
    if expected > 0:
        if actual < expected * 0.5:
            updated_state["consistency"] = max(
                0.5,
                updated_state["consistency"] - 0.05
            )
        else:
            updated_state["consistency"] = min(
                1.0,
                updated_state["consistency"] + 0.02
            )

    # -----------------------------------
    # 6. HISTORY
    # -----------------------------------
    updated_state["history"].append({
        "date": today.date().isoformat(),
        "actual_hours": actual,
        "expected_hours": expected
    })

    return updated_state
