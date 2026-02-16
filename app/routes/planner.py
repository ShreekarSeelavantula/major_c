from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

from app.services.planner_service import PlannerService


router = APIRouter(prefix="/planner", tags=["Planner"])


# -----------------------------
# Request Schema
# -----------------------------
class Topic(BaseModel):
    topic: str
    complexity: str
    estimated_hours: float


class PlanRequest(BaseModel):
    topics: List[Topic]
    learner_state: Dict[str, Any]
    hours_per_day: float
    deadline_days: int


# -----------------------------
# Route
# -----------------------------
@router.post("/generate-plan")
def generate_plan(request: PlanRequest):

    plan = PlannerService.create_plan(
        topics=[t.dict() for t in request.topics],
        learner_state=request.learner_state,
        hours_per_day=request.hours_per_day,
        deadline_days=request.deadline_days
    )

    return {
        "status": "success",
        "plan": plan
    }
