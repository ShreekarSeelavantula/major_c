from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection
from app.services.plan_orchestrator import build_adaptive_plan
from app.storage.plan_store import get_study_plan, load_plan
from app.storage.learner_store import load_learner_state, save_learner_state
from app.services.familiarity_updater import update_familiarity
from app.services.bulk_question_generator import BulkQuestionGenerator

router = APIRouter(tags=["Study Plan"])
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# Plan configuration page
# -----------------------------
@router.get("/plan/configure/{syllabus_id}", response_class=HTMLResponse)
def configure_plan(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    if not syllabus.get("structured_syllabus"):
        raise HTTPException(
            status_code=400,
            detail="Syllabus not structured yet"
        )

    return templates.TemplateResponse(
        "plan_configure.html",
        {
            "request": request,
            "syllabus_id": syllabus_id,
            "filename": syllabus["filename"]
        }
    )


# -----------------------------
# Plan generation handler
# -----------------------------
@router.post("/plan/generate")
def generate_plan(
    request: Request,
    syllabus_id: str = Form(...),
    hours_per_day: float = Form(...),
    deadline_days: int = Form(...)
):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(user_id)
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    structured_syllabus = syllabus.get("structured_syllabus")

    if not structured_syllabus:
        raise HTTPException(
            status_code=400,
            detail="Syllabus has no structured content"
        )

    request.session["last_plan_config"] = {
        "syllabus_id": syllabus_id,
        "hours_per_day": hours_per_day,
        "deadline_days": deadline_days
    }

    result = build_adaptive_plan(
        user_id=user_id,
        structured_syllabus=structured_syllabus,
        hours_per_day=hours_per_day,
        deadline_days=deadline_days
    )

    return RedirectResponse(
        url=f"/plan/view/{result['plan_id']}",
        status_code=303
    )


# -----------------------------
# Plan view page
# -----------------------------
@router.get("/plan/view/{plan_id}", response_class=HTMLResponse)
def view_plan(request: Request, plan_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id  = request.session["user_id"]
    plan_doc = get_study_plan(plan_id=plan_id, user_id=user_id)

    if not plan_doc:
        raise HTTPException(status_code=404, detail="Plan not found")

    schedule   = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    syllabus = syllabus_collection.find_one(
        {"user_id": ObjectId(user_id), "status": "structured"},
        sort=[("_id", -1)]
    )
    syllabus_id = str(syllabus["_id"]) if syllabus else None

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plan_latest",
            "schedule": schedule,
            "confidence": confidence,
            "syllabus_id": syllabus_id,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at":    plan_doc.get("created_at")
            }
        }
    )


@router.get("/plan/latest", response_class=HTMLResponse)
def view_latest_plan(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id  = request.session["user_id"]
    plan_doc = load_plan(user_id)

    if not plan_doc:
        return RedirectResponse("/dashboard", status_code=303)

    schedule   = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    syllabus = syllabus_collection.find_one(
        {"user_id": ObjectId(user_id), "status": "structured"},
        sort=[("_id", -1)]
    )
    syllabus_id = str(syllabus["_id"]) if syllabus else None

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plan_latest",
            "schedule": schedule,
            "confidence": confidence,
            "syllabus_id": syllabus_id,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at":    plan_doc.get("created_at")
            }
        }
    )


# -----------------------------
# Dynamic Plan page
# -----------------------------
@router.get("/plan/dynamic", response_class=HTMLResponse)
def dynamic_plan(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id  = request.session["user_id"]
    plan_doc = load_plan(user_id)

    if not plan_doc:
        return RedirectResponse("/dashboard", status_code=303)

    schedule   = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    syllabus = syllabus_collection.find_one(
        {"user_id": ObjectId(user_id), "status": "structured"},
        sort=[("_id", -1)]
    )
    syllabus_id = str(syllabus["_id"]) if syllabus else None

    return templates.TemplateResponse(
        "dynamic_plan.html",
        {
            "request": request,
            "active_page": "dynamic_plan",
            "schedule": schedule,
            "confidence": confidence,
            "syllabus_id": syllabus_id,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at":    plan_doc.get("created_at")
            }
        }
    )


# ─────────────────────────────────────────────
# Daily Quiz — get questions
# GET /plan/quiz/questions/{day}
# No syllabus_id in URL — finds bank automatically
# ─────────────────────────────────────────────
@router.get("/plan/quiz/questions/{day}")
async def get_daily_quiz_questions(request: Request, day: int):

    if "user_id" not in request.session:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)

    user_id = request.session["user_id"]

    # 1. Load plan
    plan_doc = load_plan(user_id)
    if not plan_doc:
        return JSONResponse({"error": "no_plan"}, status_code=404)

    schedule  = plan_doc["plan"].get("schedule", {})
    day_tasks = schedule.get(str(day)) or schedule.get(day, [])

    if not day_tasks:
        return JSONResponse({"error": "no_tasks_for_day"}, status_code=404)

    # 2. Get study topics for this day
    study_topics = [
        t["topic"] for t in day_tasks
        if t.get("type") == "study"
    ]

    if not study_topics:
        return JSONResponse({"error": "no_topics_for_day"}, status_code=404)

    # 3. Find the right question bank automatically
    #    Try all structured syllabuses for this user, newest first
    syllabuses = list(syllabus_collection.find(
        {"user_id": ObjectId(user_id), "status": "structured"},
        sort=[("_id", -1)]
    ))

    bank = None
    for syllabus in syllabuses:
        candidate = BulkQuestionGenerator.load_question_bank(
            str(syllabus["_id"])
        )
        if candidate and any(t in candidate for t in study_topics):
            bank = candidate
            break

    # 4. Build questions — 1 per topic for daily quiz
    questions = {}
    topic_map = {}

    for i, topic in enumerate(study_topics):
        topic_id          = f"t{i}"
        topic_map[topic_id] = topic

        if bank and topic in bank and bank[topic]:
            questions[topic_id] = [bank[topic][0]]
        else:
            questions[topic_id] = [{
                "question": f"Which of the following best describes '{topic}'?",
                "options": [
                    "A core concept in this subject",
                    "An unrelated technical term",
                    "A programming tool",
                    "A hardware component"
                ],
                "answer": "A core concept in this subject"
            }]

    return JSONResponse({
        "questions":       questions,
        "topic_map":       topic_map,
        "day":             day,
        "total_questions": len(questions)
    })


# ─────────────────────────────────────────────
# Daily Quiz — submit answers
# POST /plan/quiz/submit
# ─────────────────────────────────────────────
@router.post("/plan/quiz/submit")
async def submit_daily_quiz(request: Request):

    if "user_id" not in request.session:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)

    user_id = request.session["user_id"]
    body    = await request.json()

    answers   = body.get("answers", {})
    questions = body.get("questions", {})
    topic_map = body.get("topic_map", {})

    topic_scores  = {}
    total_q       = 0
    total_correct = 0

    for topic_id, qs in questions.items():
        real_topic    = topic_map.get(topic_id, topic_id)
        correct_count = 0

        for i, q in enumerate(qs):
            key = f"{topic_id}_{i}"
            total_q += 1
            if answers.get(key, "").strip().lower() == q.get("answer", "").strip().lower():
                correct_count += 1
                total_correct += 1

        topic_scores[real_topic] = correct_count / len(qs) if qs else 0

    overall_score = total_correct / total_q if total_q else 0

    learner_state = load_learner_state(user_id) or {"topic_states": {}}
    learner_state = update_familiarity(learner_state, topic_scores)
    save_learner_state(user_id, learner_state)

    return JSONResponse({
        "overall_score":   round(overall_score * 100, 1),
        "total_correct":   total_correct,
        "total_questions": total_q,
        "topic_scores": {
            t: round(s * 100, 1) for t, s in topic_scores.items()
        }
    })