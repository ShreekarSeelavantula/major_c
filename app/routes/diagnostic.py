from fastapi import APIRouter
from app.services.diagnostic_service import DiagnosticService

router = APIRouter()
diagnostic_service = DiagnosticService()


@router.post("/diagnostic/start")
def start_diagnostic(topics: list):
    """
    Generate diagnostic questions for given topics.
    """

    questions = diagnostic_service.generate_questions(topics)

    return {
        "questions": questions
    }


@router.post("/diagnostic/evaluate")
def evaluate_diagnostic(payload: dict):

    questions = payload["questions"]
    answers = payload["answers"]

    scores = diagnostic_service.evaluate_answers(questions, answers)

    return {
        "topic_familiarity": scores
    }