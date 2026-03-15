from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection
from app.services.plan_orchestrator import build_adaptive_plan
from app.storage.plan_store import get_study_plan, load_plan

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

    # Store config for later re-generation
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

    user_id = request.session["user_id"]

    plan_doc = get_study_plan(
        plan_id=plan_id,
        user_id=user_id
    )

    if not plan_doc:
        raise HTTPException(status_code=404, detail="Plan not found")

    # plan_doc["plan"] has keys: "schedule" and "confidence"
    schedule = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plan_latest",
            "schedule": schedule,
            "confidence": confidence,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at": plan_doc.get("created_at")
            }
        }
    )


# -----------------------------
# View latest plan for user
# -----------------------------
@router.get("/plan/latest", response_class=HTMLResponse)
def view_latest_plan(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    user_id = request.session["user_id"]

    plan_doc = load_plan(user_id)

    if not plan_doc:
        return RedirectResponse("/dashboard", status_code=303)

    schedule = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plan_latest",
            "schedule": schedule,
            "confidence": confidence,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at": plan_doc.get("created_at")
            }
        }
    )