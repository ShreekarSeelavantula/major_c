"""
run_once_fix.py  —  run this ONCE from project root to fix the stale plan.

Usage:
    cd /workspaces/major_c
    python run_once_fix.py

What it does:
1. Cleans dirty/generic topic names from learner state
   (e.g. "Definition", "Types", "Labor", "Framework", "sign on", etc.)
2. Resets learning_speed and consistency floor so plan isn't too cramped
3. Regenerates the adaptive plan with the NEW generator logic
4. Saves both files back

You only need to run this once.
"""

import json
import os
import sys

sys.path.insert(0, os.getcwd())

LEARNER_PATH = "data/learners/697872ebfc9e66d2a16ea0c6.json"
PLAN_PATH    = "data/plans/697872ebfc9e66d2a16ea0c6.json"

# ── Topics to REMOVE from learner state (generic / dirty) ──
REMOVE_TOPICS = {
    "Definition", "Types", "Labor", "Emotional", "Intelligence",
    "Theories", "Management", "Intervention", "Emotions",
    "Framework", "Frame work", "Types of Management", "Labour",
    "Theories.", "Introduction", "basics",
    "sign on", "Cross site Scripting Vulnerability.",
    "Virtual Elections, Single",
    "Importance, Factors influencing perception, Interpersonal perception- Impression Management. Motivation, importance,",
}

# ── Load learner state ──
with open(LEARNER_PATH) as f:
    learner = json.load(f)

# ── Remove dirty topics ──
before = len(learner["topic_states"])
for topic in list(learner["topic_states"].keys()):
    if topic in REMOVE_TOPICS:
        print(f"  Removing dirty topic: '{topic}'")
        del learner["topic_states"][topic]

after = len(learner["topic_states"])
print(f"\nCleaned {before - after} dirty topics. {after} topics remain.")

# ── Lift learning_speed and consistency so plan isn't too cramped ──
# Current values: learning_speed=0.7, consistency=0.5 → effective hours = 1.68/day
# These are accurate — don't override them.
# The new generator already handles the floor (max 1.0 effective hours)
# and the familiarity discount (less time for known topics).
# Just ensure they are within sane bounds.
learner["learning_speed"] = max(0.7, min(1.5, learner.get("learning_speed", 1.0)))
learner["consistency"]    = max(0.5, min(1.0, learner.get("consistency", 1.0)))

print(f"\nlearning_speed = {learner['learning_speed']}")
print(f"consistency    = {learner['consistency']}")

# ── Save cleaned learner state ──
with open(LEARNER_PATH, "w") as f:
    json.dump(learner, f, indent=2)
print(f"\n✅ Learner state saved: {LEARNER_PATH}")

# ── Now regenerate the plan ──
print("\nRegenerating plan...")

from app.services.plan_orchestrator import build_adaptive_plan
from app.storage.plan_store import load_plan

# Load plan metadata (hours, deadline)
plan_doc = load_plan("697872ebfc9e66d2a16ea0c6")
hours    = plan_doc.get("hours_per_day", 3.0) if plan_doc else 3.0
deadline = plan_doc.get("deadline_days", 30)  if plan_doc else 30

# Load syllabus from MongoDB
from app.database import syllabus_collection
from bson import ObjectId

syllabus = syllabus_collection.find_one({
    "user_id": ObjectId("697872ebfc9e66d2a16ea0c6"),
    "status": "structured"
})

if not syllabus:
    print("❌ No structured syllabus found in MongoDB.")
    sys.exit(1)

result = build_adaptive_plan(
    user_id="697872ebfc9e66d2a16ea0c6",
    structured_syllabus=syllabus["structured_syllabus"],
    hours_per_day=hours,
    deadline_days=deadline
)

print(f"✅ Plan regenerated! plan_id = {result['plan_id']}")

# ── Verify variety in first 10 days ──
schedule = result["plan"]["schedule"]
print("\nFirst 10 days preview:")
for day in list(schedule.keys())[:10]:
    topics = [t["topic"] for t in schedule[day] if t["type"] == "study"]
    print(f"  Day {day}: {topics}")