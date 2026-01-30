from app.core.adaptive_plan_generator import generate_adaptive_plan
from datetime import date, timedelta

# =====================================================
# 1. SIMULATED SYLLABUS PIPELINE OUTPUT
# (Matches syllabus_pipeline.process_syllabus)
# =====================================================

topics = [
    {
        "topic": "Introduction to DBMS",
        "complexity": "Easy",
        "estimated_hours": 0.5
    },
    {
        "topic": "ER Model",
        "complexity": "Easy",
        "estimated_hours": 1.0
    },
    {
        "topic": "Relational Algebra",
        "complexity": "Medium",
        "estimated_hours": 1.5
    },
    {
        "topic": "Normalization",
        "complexity": "Hard",
        "estimated_hours": 2.5
    },
    {
        "topic": "Indexing",
        "complexity": "Medium",
        "estimated_hours": 2.0
    }
]

# =====================================================
# 2. SIMULATED LEARNER STATE SNAPSHOT
# =====================================================

learner_state = {
    "learning_speed": 1.0,
    "topic_states": {
        "Introduction to DBMS": {"familiarity": 0.7},
        "ER Model": {"familiarity": 0.6},
        "Relational Algebra": {"familiarity": 0.3},
        "Normalization": {"familiarity": 0.1},
        "Indexing": {"familiarity": 0.2},
    }
}

# =====================================================
# 3. STUDY CONSTRAINTS
# =====================================================

hours_per_day = 3
deadline_days = 7

# =====================================================
# 4. GENERATE ADAPTIVE STUDY PLAN
# =====================================================

plan = generate_adaptive_plan(
    topics=topics,
    learner_state=learner_state,
    hours_per_day=hours_per_day,
    deadline_days=deadline_days
)

# =====================================================
# 5. PRINT PLAN (HUMAN READABLE)
# =====================================================

print("\n📅 ADAPTIVE STUDY PLAN\n")

for day in sorted(plan.keys()):
    print(f"📌 Day {day}")
    total_time = 0

    for session in plan[day]:
        if session["type"] == "study":
            print(
                f"   📖 {session['topic']} "
                f"(complexity={session['complexity']}, "
                f"time={session['hours']}h)"
            )
            total_time += session["hours"]

        elif session["type"] == "revision":
            print(f"   🔁 Revision Session ({session['hours']}h)")
            total_time += session["hours"]

        elif session["type"] == "micro_test":
            print(f"   🧪 Micro Familiarity Test ({session['questions']} questions)")

    print(f"   ⏱ Total Study Time: {round(total_time, 2)}h\n")

print("✅ Simulation complete.")
