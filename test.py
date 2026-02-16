from datetime import datetime, timedelta
from pprint import pprint

from adaptive_plan_generator import generate_adaptive_plan
from retention_scheduler import apply_retention_decay


# -------------------------
# Sample Topics
# -------------------------
topics = [
    {"topic": "Arrays", "complexity": "Easy", "estimated_hours": 4},
    {"topic": "Linked Lists", "complexity": "Medium", "estimated_hours": 6},
    {"topic": "Dynamic Programming", "complexity": "Hard", "estimated_hours": 8},
]


# -------------------------
# Sample Learner State
# -------------------------
learner_state = {
    "learning_speed": 1.0,
    "consistency": 1.0,
    "topic_states": {
        "Arrays": {
            "familiarity": 0.4,
            "confidence": 0.5,
            "retention": 0.6,
            "complexity": "Easy",
            "last_studied": (datetime.utcnow() - timedelta(days=6)).strftime("%Y-%m-%d")
        },
        "Linked Lists": {
            "familiarity": 0.3,
            "confidence": 0.4,
            "retention": 0.5,
            "complexity": "Medium",
            "last_studied": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
        }
    }
}


# Apply retention decay
learner_state = apply_retention_decay(learner_state)


# Generate Plan
plan = generate_adaptive_plan(
    topics,
    learner_state,
    hours_per_day=3,
    deadline_days=7
)


print("\n========== ADAPTIVE PLAN ==========\n")
pprint(plan)
