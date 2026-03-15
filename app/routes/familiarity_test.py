from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection

from app.services.bulk_question_generator import BulkQuestionGenerator
from app.services.familiarity_updater import update_familiarity
from app.services.test_sampler import sample_initial_unit_topics, sample_micro_topics

from app.storage.learner_store import load_learner_state, save_learner_state

import json
import random

router = APIRouter(tags=["Familiarity Test"])

templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------
# HELPER: ensure question bank exists for syllabus
# ---------------------------------------------------
def _ensure_question_bank(syllabus: dict) -> dict:
    """
    Build question bank if not already built.
    Returns the bank { topic_name: [questions] }
    """
    syllabus_id = str(syllabus["_id"])
    domain = syllabus.get("title") or syllabus.get("subject") or ""

    bank = BulkQuestionGenerator.load_question_bank(syllabus_id)

    if not bank:
        structured = syllabus.get("structured_syllabus", [])
        bank = BulkQuestionGenerator.build_question_bank(
            syllabus_id=syllabus_id,
            structured_syllabus=structured,
            domain=domain
        )

    return bank


# ---------------------------------------------------
# HELPER: build questions + topic_map from topic list
# ---------------------------------------------------
def _build_test_from_bank(bank: dict, topic_names: list) -> tuple:
    """
    Given a bank and a list of topic names, return
    (questions dict, topic_map dict) ready for the template.

    Falls back to a placeholder question if topic missing from bank.
    """
    questions = {}
    topic_map = {}

    for i, topic in enumerate(topic_names):
        topic_id = f"t{i}"
        topic_map[topic_id] = topic

        if topic in bank and bank[topic]:
            questions[topic_id] = bank[topic]
        else:
            # Fallback placeholder — no extra API call needed
            questions[topic_id] = [
                {
                    "question": f"Which of the following best describes '{topic}'?",
                    "options": [
                        f"A core concept in the subject",
                        f"An unrelated technical term",
                        f"A programming tool",
                        f"A hardware component"
                    ],
                    "answer": "A core concept in the subject"
                }
            ]

    return questions, topic_map


# ---------------------------------------------------
# START FAMILIARITY TEST  (Unit-1 diagnostic)
# ---------------------------------------------------
@router.get("/familiarity/start/{syllabus_id}", response_class=HTMLResponse)
async def start_familiarity_test(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(user_id)
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    structured = syllabus.get("structured_syllabus")

    if not structured:
        raise HTTPException(status_code=400, detail="Structured syllabus missing")

    # ⭐ Ensure question bank is built (one API call total)
    bank = _ensure_question_bank(syllabus)

    # ⭐ Initial test = ALL Unit-1 topics (proper diagnostic)
    # sample_initial_unit_topics picks from first unit only, up to 20
    unit1_topics = sample_initial_unit_topics(structured, n=20)

    if not unit1_topics:
        # Fallback: first 10 topics from anywhere
        unit1_topics = [
            t["name"]
            for unit in structured
            for t in unit["topics"]
        ][:10]

    questions, topic_map = _build_test_from_bank(bank, unit1_topics)

    request.session["test_questions"] = questions
    request.session["test_topic_map"] = topic_map
    request.session["test_syllabus_id"] = syllabus_id
    request.session["test_type"] = "initial"

    return templates.TemplateResponse(
        "familiarity_test.html",
        {
            "request": request,
            "questions": questions,
            "topic_map": topic_map,
            "syllabus_id": syllabus_id,
            "test_type": "initial",
            "error_message": None
        }
    )


# ---------------------------------------------------
# MICRO TEST  (Periodic 10-question test)
# ---------------------------------------------------
@router.get("/familiarity/micro/{syllabus_id}", response_class=HTMLResponse)
async def micro_familiarity_test(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]
    learner_state = load_learner_state(user_id) or {"topic_states": {}}

    syllabus = syllabus_collection.find_one({"_id": ObjectId(syllabus_id)})

    if not syllabus:
        raise HTTPException(status_code=404)

    structured = syllabus.get("structured_syllabus", [])

    # ⭐ Load bank — no new API call
    bank = _ensure_question_bank(syllabus)

    # Sample 10 weak/random topics for micro test
    topics = sample_micro_topics(structured, learner_state, n=10)

    questions, topic_map = _build_test_from_bank(bank, topics)

    request.session["test_questions"] = questions
    request.session["test_topic_map"] = topic_map
    request.session["test_syllabus_id"] = syllabus_id
    request.session["test_type"] = "micro"

    return templates.TemplateResponse(
        "familiarity_test.html",
        {
            "request": request,
            "questions": questions,
            "topic_map": topic_map,
            "syllabus_id": syllabus_id,
            "test_type": "micro",
            "error_message": None
        }
    )


# ---------------------------------------------------
# LOCAL QUESTIONS  (Fallback — no AI needed)
# ---------------------------------------------------
@router.get("/familiarity/local/{syllabus_id}", response_class=HTMLResponse)
async def local_familiarity_test(request: Request, syllabus_id: str):

    local_questions = {
        "t0": [
            {
                "question": "What is Python?",
                "options": ["Language", "Database", "OS", "Compiler"],
                "answer": "Language"
            }
        ],
        "t1": [
            {
                "question": "Which structure uses FIFO?",
                "options": ["Stack", "Queue", "Tree", "Graph"],
                "answer": "Queue"
            }
        ]
    }

    topic_map = {
        "t0": "Python Basics",
        "t1": "Data Structures"
    }

    request.session["test_questions"] = local_questions
    request.session["test_topic_map"] = topic_map
    request.session["test_syllabus_id"] = syllabus_id

    return templates.TemplateResponse(
        "familiarity_test.html",
        {
            "request": request,
            "questions": local_questions,
            "topic_map": topic_map,
            "syllabus_id": syllabus_id,
            "test_type": "local",
            "error_message": None
        }
    )


# ---------------------------------------------------
# SUBMIT TEST
# ---------------------------------------------------
@router.post("/familiarity/submit")
async def submit_familiarity_test(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    answers = dict(form)

    questions = request.session.get("test_questions")
    topic_map = request.session.get("test_topic_map")

    # Stateless fallback (important for Codespaces)
    if not questions or not topic_map:
        try:
            questions = json.loads(form.get("questions_json"))
            topic_map = json.loads(form.get("topic_map_json"))
        except:
            raise HTTPException(
                status_code=400,
                detail="Test data lost. Please restart test."
            )

    topic_scores = {}
    total_q = 0
    total_correct = 0

    for topic_id, qs in questions.items():

        real_topic = topic_map.get(topic_id, topic_id)
        correct_count = 0

        for i, q in enumerate(qs):

            key = f"{topic_id}_{i}"
            total_q += 1

            user_answer = answers.get(key, "").strip().lower()
            correct_text = q.get("answer", "").strip().lower()

            print(f"Q         : {key}")
            print(f"User ans  : '{user_answer}'")
            print(f"Correct   : '{correct_text}'")
            print(f"Match     : {user_answer == correct_text}")
            print("---")

            if user_answer == correct_text:
                correct_count += 1
                total_correct += 1

        topic_scores[real_topic] = (
            correct_count / len(qs) if qs else 0
        )

    overall_score = total_correct / total_q if total_q else 0

    user_id = request.session["user_id"]
    learner_state = load_learner_state(user_id) or {"topic_states": {}}

    learner_state = update_familiarity(learner_state, topic_scores)
    save_learner_state(user_id, learner_state)

    request.session["last_test_result"] = {
        "topic_scores": topic_scores,
        "overall_score": overall_score
    }

    test_type = request.session.get("test_type", "")
    syllabus_id = request.session.get("test_syllabus_id", "")

    # --------------------------------------------------
    # MICRO TEST → redirect back to Today's page
    # Mark micro test as completed so Today UI updates
    # --------------------------------------------------
    if test_type == "micro" and syllabus_id:

        # Store micro test result for Today's page to display
        request.session["micro_test_done_today"] = {
            "syllabus_id": syllabus_id,
            "score": round(overall_score * 100, 1),
            "topics_tested": len(topic_scores)
        }

        # Clean up test session keys
        for key in ["test_questions", "test_topic_map",
                    "test_syllabus_id", "test_type"]:
            request.session.pop(key, None)

        return RedirectResponse(
            url=f"/progress/today/{syllabus_id}",
            status_code=303
        )

    # --------------------------------------------------
    # INITIAL TEST → go to result page
    # Show "Rate Remaining Units" button
    # --------------------------------------------------
    if test_type == "initial" and syllabus_id:
        request.session["pending_self_rating_syllabus_id"] = syllabus_id

    return RedirectResponse(url="/familiarity/result", status_code=303)


# ---------------------------------------------------
# RESULT PAGE
# ---------------------------------------------------
@router.get("/familiarity/result", response_class=HTMLResponse, name="familiarity_result")
async def familiarity_result(request: Request):

    result = request.session.get("last_test_result")

    if not result:
        return RedirectResponse("/dashboard", status_code=303)

    syllabus_id = request.session.get("pending_self_rating_syllabus_id")

    response = templates.TemplateResponse(
        "test_result.html",
        {
            "request": request,
            "result": result,
            # ⭐ Pass syllabus_id so result page can show
            # "Continue to self-rating" button if needed
            "syllabus_id": syllabus_id
        }
    )

    for key in ["last_test_result", "test_questions", "test_topic_map",
                "test_syllabus_id", "test_type"]:
        request.session.pop(key, None)

    return response


# ---------------------------------------------------
# SELF-RATING SURVEY  (Units 2–5)
# ---------------------------------------------------
@router.get("/familiarity/self-rating/{syllabus_id}", response_class=HTMLResponse)
async def self_rating_page(request: Request, syllabus_id: str):
    """
    Show self-rating survey for all units EXCEPT Unit-1.
    Unit-1 was already tested in the diagnostic test.
    """

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    structured = syllabus.get("structured_syllabus", [])

    # Show all units except Unit-1 (already tested)
    units_to_rate = [
        u for u in structured
        if u.get("unit_number", 1) != 1
    ]

    if not units_to_rate:
        # Only one unit — skip self-rating, go to dashboard
        return RedirectResponse("/dashboard", status_code=303)

    # Store syllabus_id in session so submit can redirect properly
    request.session["pending_self_rating_syllabus_id"] = syllabus_id

    return templates.TemplateResponse(
        "self_rating.html",
        {
            "request": request,
            "units": units_to_rate,
            "syllabus_id": syllabus_id
        }
    )


# ---------------------------------------------------
# SELF-RATING SUBMIT
# ---------------------------------------------------
@router.post("/familiarity/self-rating/submit")
async def submit_self_rating(request: Request):
    """
    Process self-rating form.

    For each rated unit, apply the self-rating score to
    ALL topics in that unit with lower confidence weight
    (0.4 * self_rating) since self-rating is less reliable
    than an actual test.

    Formula from project plan:
    familiarity = 0.6 * test_score + 0.4 * self_rating
    For self-rating only (no test yet):
    familiarity = 0.4 * self_rating
    """

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    answers = dict(form)

    syllabus_id = answers.get("syllabus_id")
    user_id = request.session["user_id"]

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(user_id)
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    structured = syllabus.get("structured_syllabus", [])

    # Load existing learner state (has Unit-1 test results)
    learner_state = load_learner_state(user_id) or {"topic_states": {}}

    if "topic_states" not in learner_state:
        learner_state["topic_states"] = {}

    # Process each unit's self-rating
    for unit in structured:
        unit_number = unit.get("unit_number", 1)

        if unit_number == 1:
            # Skip Unit-1 — already tested properly
            continue

        form_key = f"unit_{unit_number}"
        raw_rating = answers.get(form_key)

        if raw_rating is None:
            continue

        try:
            self_rating = float(raw_rating)
        except ValueError:
            continue

        # Apply to all topics in this unit
        # Weight = 0.4 because self-rating is less reliable than MCQ test
        weighted_familiarity = round(0.4 * self_rating, 3)

        for topic in unit.get("topics", []):
            topic_name = topic["name"]
            existing = learner_state["topic_states"].get(topic_name, {})

            # If topic already has test data, blend with self-rating
            # If topic is fresh, use weighted self-rating only
            existing_familiarity = existing.get("familiarity", 0.0)
            existing_attempts = existing.get("attempts", 0)

            if existing_attempts > 0:
                # Blend: existing test score takes priority (60%)
                blended = round(
                    0.6 * existing_familiarity + 0.4 * self_rating,
                    3
                )
            else:
                blended = weighted_familiarity

            learner_state["topic_states"][topic_name] = {
                "familiarity": blended,
                "confidence": round(blended * 0.6, 3),  # lower confidence for self-rated
                "retention": existing.get("retention", 1.0),
                "attempts": existing_attempts,
                "revision_due": blended < 0.5,
                "last_updated": existing.get("last_updated"),
                "self_rated": True   # flag so planner knows this is approximate
            }

    save_learner_state(user_id, learner_state)

    # Clear pending flag
    request.session.pop("pending_self_rating_syllabus_id", None)

    # ⭐ Regenerate plan now that all units have familiarity data
    # Self-rating just filled in Units 2-5 — plan should reflect this
    from app.services.plan_orchestrator import build_adaptive_plan
    from app.storage.plan_store import load_plan

    try:
        plan_doc = load_plan(user_id)
        hours_per_day = plan_doc.get("hours_per_day", 3) if plan_doc else 3
        deadline_days = plan_doc.get("deadline_days", 30) if plan_doc else 30

        result = build_adaptive_plan(
            user_id=user_id,
            structured_syllabus=structured,
            hours_per_day=hours_per_day,
            deadline_days=deadline_days
        )

        # ⭐ Go straight to plan — user wants to see their plan immediately
        return RedirectResponse(
            url=f"/plan/view/{result['plan_id']}",
            status_code=303
        )

    except Exception as e:
        print(f"Plan regeneration after self-rating failed: {e}")
        # Fallback to dashboard if plan generation fails
        return RedirectResponse("/dashboard", status_code=303)