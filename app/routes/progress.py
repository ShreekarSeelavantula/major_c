from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import date
import json

from app.database import syllabus_collection
from app.storage.learner_store import load_learner_state, save_learner_state
from app.storage.plan_store import load_plan, save_plan
from app.core.learner_updater import update_learner_state
from app.services.plan_orchestrator import build_adaptive_plan
from app.services.test_sampler import all_units_tested

router = APIRouter(tags=["Progress"])
templates = Jinja2Templates(directory="app/templates")


# --------------------------------------------------
# HELPER: get today's day number in the plan
# --------------------------------------------------
def _get_today_day_number(plan_doc: dict) -> int:
    created_at = plan_doc.get("created_at")

    if not created_at:
        return 1

    if isinstance(created_at, str):
        from datetime import datetime
        try:
            created_date = datetime.fromisoformat(created_at).date()
        except Exception:
            return 1
    else:
        created_date = created_at.date() if hasattr(created_at, "date") else date.today()

    days_passed = (date.today() - created_date).days + 1
    deadline_days = plan_doc.get("deadline_days", 30)

    return max(1, min(days_passed, deadline_days))


# --------------------------------------------------
# TODAY'S TASKS PAGE
# --------------------------------------------------
@router.get("/progress/today/{syllabus_id}", response_class=HTMLResponse)
def today_tasks(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]

    # Load plan
    plan_doc = load_plan(user_id)

    if not plan_doc:
        return RedirectResponse(
            f"/plan/configure/{syllabus_id}",
            status_code=303
        )

    # ⭐ Clear micro_test_done_today if it's from a different syllabus
    mt_done = request.session.get("micro_test_done_today", {})
    if mt_done.get("syllabus_id") != syllabus_id:
        request.session.pop("micro_test_done_today", None)

    schedule = plan_doc["plan"].get("schedule", {})
    today_day = _get_today_day_number(plan_doc)

    # Get today's tasks — try exact day, fallback to nearest available day
    today_tasks_list = schedule.get(str(today_day)) or schedule.get(today_day)

    if not today_tasks_list:
        available_days = [int(d) for d in schedule.keys()]
        if available_days:
            nearest = min(available_days, key=lambda d: abs(d - today_day))
            today_tasks_list = schedule.get(str(nearest), [])
        else:
            today_tasks_list = []

    # Separate task types
    study_tasks = [t for t in today_tasks_list if t.get("type") == "study"]
    revision_tasks = [t for t in today_tasks_list if t.get("type") == "revision"]
    micro_test = next(
        (t for t in today_tasks_list if t.get("type") == "micro_test"),
        None
    )

    # Calculate planned hours for today
    planned_hours = sum(
        t.get("hours", 0)
        for t in today_tasks_list
        if t.get("type") in ("study", "revision")
    )

    # --------------------------------------------------
    # ⭐ MICRO TEST POPUP LOGIC
    # Check if there are still self-rated units that need
    # proper testing. If yes, show the popup on Today's page.
    # --------------------------------------------------
    show_micro_popup = False
    next_unit_to_test = None

    learner_state_check = load_learner_state(user_id) or {}

    # Only bother checking if learner state exists
    if learner_state_check:
        syllabus_doc = syllabus_collection.find_one(
            {"_id": ObjectId(syllabus_id)}
        )

        if syllabus_doc:
            structured_check = syllabus_doc.get("structured_syllabus", [])

            if structured_check and not all_units_tested(
                structured_check, learner_state_check
            ):
                show_micro_popup = True

                # Find which unit is next to be properly tested
                tested = set(learner_state_check.get("tested_units", []))

                for unit in structured_check:
                    u_num = unit.get("unit_number", 1)

                    # Unit-1 is always tested in initial diagnostic
                    if u_num == 1:
                        continue

                    if u_num not in tested:
                        next_unit_to_test = unit.get(
                            "title",
                            f"Unit {u_num}"
                        )
                        break

    return templates.TemplateResponse(
        "today.html",
        {
            "request": request,
            "syllabus_id": syllabus_id,
            "day_number": today_day,
            "study_tasks": study_tasks,
            "revision_tasks": revision_tasks,
            "micro_test": micro_test,
            "planned_hours": round(planned_hours, 2),
            "deadline_days": plan_doc.get("deadline_days", 30),
            "hours_per_day": plan_doc.get("hours_per_day", 3),
            # ⭐ Popup trigger variables
            "show_micro_popup": show_micro_popup,
            "next_unit_to_test": next_unit_to_test
        }
    )


# --------------------------------------------------
# MARK DONE — submit completed tasks
# --------------------------------------------------
@router.post("/progress/submit/{syllabus_id}")
async def submit_progress(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]
    form = await request.form()
    answers = dict(form)

    # ------------------------------------------------
    # 1. Parse completed tasks from form
    # ------------------------------------------------
    completed_topics = []
    for key, value in answers.items():
        if key.startswith("done__") and value == "on":
            topic_name = key.replace("done__", "")
            completed_topics.append(topic_name)

    try:
        actual_hours = float(answers.get("actual_hours", 0))
    except ValueError:
        actual_hours = 0.0

    expected_hours = float(answers.get("expected_hours", 0))

    # ------------------------------------------------
    # 2. Build daily_report for learner_updater
    # ------------------------------------------------
    study_sessions = [
        {
            "topic_id": topic,
            "hours": round(
                actual_hours / max(len(completed_topics), 1),
                2
            )
        }
        for topic in completed_topics
    ]

    daily_report = {
        "study_sessions": study_sessions,
        "micro_tests": [],
        "actual_hours": actual_hours,
        "expected_hours": expected_hours
    }

    # ------------------------------------------------
    # 3. Update learner state
    # ------------------------------------------------
    learner_state = load_learner_state(user_id)

    if not learner_state:
        learner_state = {
            "topic_states": {},
            "learning_speed": 1.0,
            "consistency": 1.0,
            "history": []
        }

    learner_state = update_learner_state(
        learner_state=learner_state,
        daily_report=daily_report
    )

    save_learner_state(user_id, learner_state)

    # ------------------------------------------------
    # 4. Auto regenerate plan with updated learner state
    # ------------------------------------------------
    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(user_id)
    })

    if syllabus and syllabus.get("structured_syllabus"):

        plan_doc = load_plan(user_id)
        hours_per_day = plan_doc.get("hours_per_day", 3) if plan_doc else 3
        deadline_days = plan_doc.get("deadline_days", 30) if plan_doc else 30

        try:
            result = build_adaptive_plan(
                user_id=user_id,
                structured_syllabus=syllabus["structured_syllabus"],
                hours_per_day=hours_per_day,
                deadline_days=deadline_days
            )

            request.session["progress_message"] = (
                f"✅ Progress saved! "
                f"Completed {len(completed_topics)} topic(s) "
                f"in {actual_hours} hrs. Plan updated."
            )

        except Exception as e:
            print(f"Plan regeneration failed: {e}")
            request.session["progress_message"] = (
                "✅ Progress saved! Plan will update on next view."
            )

    return RedirectResponse(
        url=f"/progress/today/{syllabus_id}",
        status_code=303
    )