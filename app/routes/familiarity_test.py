from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection

from app.services.ai_question_generator import AIQuestionGenerator
from app.services.test_evaluator import TestEvaluator
from app.services.familiarity_updater import update_familiarity
from app.services.test_sampler import sample_micro_topics

from app.storage.learner_store import load_learner_state, save_learner_state

import json

router = APIRouter(tags=["Familiarity Test"])

templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------
# START FAMILIARITY TEST
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

    # ⭐ FIX 1: Grab subject/title so AI generates domain-relevant questions
    syllabus_title = syllabus.get("title", "") or syllabus.get("subject", "") or ""

    topics = []
    for unit in structured:
        for topic in unit["topics"]:
            topics.append(topic["name"])

    topics = topics[:5]

    questions = {}
    topic_map = {}
    error_message = None

    for t_index, topic in enumerate(topics):
        topic_id = f"t{t_index}"

        try:
            mcqs = AIQuestionGenerator.generate_mcqs(
                topic,
                num_questions=3,
                domain=syllabus_title      # ⭐ domain context added
            )
        except Exception as e:
            error_message = "Some AI questions failed. Local fallback used."
            mcqs = [
                {
                    "question": f"Basic concept of {topic}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "Option A"
                }
            ]

        questions[topic_id] = mcqs
        topic_map[topic_id] = topic

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
            "error_message": error_message
        }
    )


# ---------------------------------------------------
# LOCAL QUESTIONS (Fallback)
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
            "error_message": None
        }
    )


# ---------------------------------------------------
# MICRO TEST (Adaptive Weak Topic Test)
# ---------------------------------------------------
@router.get("/familiarity/micro/{syllabus_id}", response_class=HTMLResponse)
async def micro_familiarity_test(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    learner_state = load_learner_state(request.session["user_id"])

    syllabus = syllabus_collection.find_one({"_id": ObjectId(syllabus_id)})

    if not syllabus:
        raise HTTPException(status_code=404)

    structured = syllabus.get("structured_syllabus")
    syllabus_title = syllabus.get("title", "") or syllabus.get("subject", "") or ""

    topics = sample_micro_topics(structured, learner_state, n=5)

    questions = {}
    topic_map = {}

    for i, topic in enumerate(topics):
        topic_id = f"t{i}"

        try:
            mcqs = AIQuestionGenerator.generate_mcqs(
                topic,
                num_questions=1,
                domain=syllabus_title      # ⭐ domain context added
            )
        except:
            mcqs = [
                {
                    "question": f"Basic idea of {topic}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "Option A"
                }
            ]

        questions[topic_id] = mcqs
        topic_map[topic_id] = topic

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

    # Stateless fallback (important for Codespaces where session may drop)
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

            # ⭐ FIX 2: The HTML radio button value is the raw option text
            # (e.g. "Employee well-being and productivity").
            # We just need to compare lowercased strings directly.
            # The old code tried to re-resolve the option letter AFTER the
            # user already submitted the full option text — that caused 0 matches.
            user_answer = answers.get(key, "").strip().lower()

            ai_answer = q.get("answer", "")
            options = q.get("options", [])

            # Resolve what the correct option TEXT is
            # CASE 1: AI returned a letter like "A", "B", "C", "D"
            if (
                isinstance(ai_answer, str)
                and len(ai_answer.strip()) == 1
                and ai_answer.strip().upper() in "ABCD"
            ):
                option_index = ord(ai_answer.strip().upper()) - ord("A")

                if 0 <= option_index < len(options):
                    correct_text = options[option_index].strip().lower()
                else:
                    correct_text = ai_answer.strip().lower()

            # CASE 2: AI returned full option text already
            else:
                correct_text = ai_answer.strip().lower()

            # Debug
            print(f"Q         : {key}")
            print(f"User ans  : '{user_answer}'")
            print(f"AI raw    : '{ai_answer}'")
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
    learner_state = load_learner_state(user_id)

    if not learner_state:
        learner_state = {"topic_states": {}}

    learner_state = update_familiarity(learner_state, topic_scores)
    save_learner_state(user_id, learner_state)

    # ⭐ FIX 3: Store result in session BEFORE redirect
    request.session["last_test_result"] = {
        "topic_scores": topic_scores,
        "overall_score": overall_score
    }

    print("SAVED TO SESSION:", request.session.get("last_test_result"))

    return RedirectResponse(url="/familiarity/result", status_code=303)


# ---------------------------------------------------
# RESULT PAGE
# ---------------------------------------------------
@router.get("/familiarity/result", response_class=HTMLResponse, name="familiarity_result")
async def familiarity_result(request: Request):

    result = request.session.get("last_test_result")

    print("RESULT FROM SESSION:", result)

    if not result:
        return RedirectResponse("/dashboard", status_code=303)

    # ⭐ FIX 4: Build response first, THEN clear session keys.
    # If you clear before rendering, the template gets nothing.
    response = templates.TemplateResponse(
        "test_result.html",
        {
            "request": request,
            "result": result
        }
    )

    # Clean up test-related session keys after rendering
    for key in ["last_test_result", "test_questions", "test_topic_map",
                "test_syllabus_id", "test_type"]:
        request.session.pop(key, None)

    return response