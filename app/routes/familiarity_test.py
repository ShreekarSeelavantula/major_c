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

    topics = []
    for unit in structured:
        for topic in unit["topics"]:
            topics.append(topic["name"])

    topics = topics[:5]

    questions = {}
    topic_map = {}

    error_message = None

    # ⭐ FIXED: try inside loop (partial fallback safe)
    for t_index, topic in enumerate(topics):
        topic_id = f"t{t_index}"

        try:
            mcqs = AIQuestionGenerator.generate_mcqs(
                topic,
                num_questions=3
            )
        except Exception as e:
            error_message = "Some AI questions failed. Local fallback used."
            mcqs = [
                {
                    "question": f"Basic concept of {topic}?",
                    "options": [
                        "Concept",
                        "Hardware",
                        "Networking",
                        "Database"
                    ],
                    "answer": "Concept"
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

    # ⭐ FIXED: store dict (NOT json)
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

    learner_state = load_learner_state(
        request.session["user_id"]
    )

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id)
    })

    if not syllabus:
        raise HTTPException(status_code=404)

    structured = syllabus.get("structured_syllabus")

    topics = sample_micro_topics(
        structured,
        learner_state,
        n=5
    )

    questions = {}
    topic_map = {}

    for i, topic in enumerate(topics):
        topic_id = f"t{i}"

        try:
            mcqs = AIQuestionGenerator.generate_mcqs(
                topic,
                num_questions=1
            )
        except:
            mcqs = [
                {
                    "question": f"Basic idea of {topic}?",
                    "options": [
                        "Concept",
                        "Hardware",
                        "Networking",
                        "Database"
                    ],
                    "answer": "Concept"
                }
            ]

        questions[topic_id] = mcqs
        topic_map[topic_id] = topic

    request.session["test_questions"] = questions
    request.session["test_topic_map"] = topic_map
    request.session["test_syllabus_id"] = syllabus_id
    request.session["test_type"] = "micro"

    print("SESSION DATA:", request.session)

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

    # ⭐ Stateless fallback (IMPORTANT for Codespaces)
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
            ai_answer = q.get("answer", "")

            # -------- Normalize AI Answer --------
            if isinstance(ai_answer, str):

                ai_answer = ai_answer.strip()

                # CASE 1 → AI returned option letter
                if len(ai_answer) == 1 and ai_answer.isalpha():

                    option_index = ord(ai_answer.lower()) - ord("a")

                    if 0 <= option_index < len(q.get("options", [])):
                        correct_text = q["options"][option_index].strip().lower()
                    else:
                        correct_text = ai_answer.lower()

                # CASE 2 → AI returned full text
                else:
                    correct_text = ai_answer.lower()

            else:
                correct_text = ""

            # -------- Debug Logs --------
            print("Q:", key)
            print("USER:", user_answer)
            print("AI RAW:", ai_answer)
            print("MATCH TEXT:", correct_text)

            # -------- Score --------
            if user_answer == correct_text:
                correct_count += 1
                total_correct += 1

        topic_scores[real_topic] = (
            correct_count / len(qs)
            if qs else 0
        )

    overall_score = total_correct / total_q if total_q else 0

    user_id = request.session["user_id"]

    learner_state = load_learner_state(user_id)

    if not learner_state:
        learner_state = {"topic_states": {}}

    learner_state = update_familiarity(
        learner_state,
        topic_scores
    )

    save_learner_state(
        user_id,
        learner_state
    )

    request.session["last_test_result"] = {
        "topic_scores": topic_scores,
        "overall_score": overall_score
    }

    return RedirectResponse(
        url="/familiarity/result",
        status_code=303
    )


@router.get("/familiarity/result", response_class=HTMLResponse, name="familiarity_result")
async def familiarity_result(request: Request):

    result = request.session.get("last_test_result")

    if not result:
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        "test_result.html",
        {
            "request": request,
            "result": result
        }
    )