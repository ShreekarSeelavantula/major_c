from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection

from app.services.ai_question_generator import AIQuestionGenerator
from app.services.test_evaluator import TestEvaluator
from app.services.familiarity_updater import update_familiarity

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

    topics = []

    for unit in structured:
        for topic in unit["topics"]:
            topics.append(topic["name"])

    topics = topics[:5]

    questions = {}

    error_message = None

    # ---------------------------------
    # Generate AI Questions
    # ---------------------------------
    try:

        for topic in topics:

            mcqs = AIQuestionGenerator.generate_mcqs(
                topic,
                num_questions=3
            )

            questions[topic] = mcqs

    except Exception as e:

        error_message = str(e)

        questions = {}

    # ---------------------------------
    # Store session safely
    # ---------------------------------
    request.session["test_questions"] = json.dumps(questions)

    request.session["test_syllabus_id"] = syllabus_id

    return templates.TemplateResponse(
        "familiarity_test.html",
        {
            "request": request,
            "questions": questions,
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

        "Python Basics": [
            {
                "question": "What is Python?",
                "options": ["Language", "Database", "OS", "Compiler"],
                "answer": "Language"
            },
            {
                "question": "Which keyword defines a function?",
                "options": ["func", "def", "define", "function"],
                "answer": "def"
            }
        ],

        "Data Structures": [
            {
                "question": "Which structure uses FIFO?",
                "options": ["Stack", "Queue", "Tree", "Graph"],
                "answer": "Queue"
            }
        ]

    }

    request.session["test_questions"] = json.dumps(local_questions)

    request.session["test_syllabus_id"] = syllabus_id

    return templates.TemplateResponse(
        "familiarity_test.html",
        {
            "request": request,
            "questions": local_questions,
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

    questions_json = request.session.get("test_questions")

    syllabus_id = request.session.get("test_syllabus_id")

    if not questions_json:
        raise HTTPException(status_code=400, detail="Test session expired")

    questions = json.loads(questions_json)

    evaluation = TestEvaluator.evaluate(
        questions,
        answers
    )

    topic_scores = evaluation["topic_scores"]

    user_id = request.session["user_id"]

    learner_state = load_learner_state(user_id)

    if learner_state is None:
        learner_state = {
            "topic_states": {}
        }

    learner_state = update_familiarity(
        learner_state,
        topic_scores
    )

    save_learner_state(
        user_id,
        learner_state
    )

    return RedirectResponse(
        url=f"/plan/configure/{syllabus_id}",
        status_code=303
    )