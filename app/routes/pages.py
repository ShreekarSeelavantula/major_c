from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import syllabus_collection
from app.storage.learner_store import load_learner_state
from app.storage.plan_store import load_plan

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --------------------------------------------------
# Auth guard helper
# --------------------------------------------------
def require_login(request: Request) -> bool:
    return "user_id" in request.session


# --------------------------------------------------
# Public pages
# --------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(
        "signup.html",
        {"request": request}
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


# --------------------------------------------------
# Protected pages
# --------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    user_id = request.session.get("user_id")

    # Load learner state for stats
    learner_state = load_learner_state(user_id)
    avg_familiarity = None
    learning_speed = None

    if learner_state:
        states = learner_state.get("topic_states", {}).values()
        if states:
            avg_familiarity = round(
                sum(s.get("familiarity", 0) for s in states) / len(states),
                3
            )
        learning_speed = learner_state.get("learning_speed")

    # Load most recent syllabus for this user
    syllabus = syllabus_collection.find_one(
        {
            "user_id": ObjectId(user_id),
            "status": "structured"
        },
        sort=[("_id", -1)]   # most recent first
    )

    syllabus_id = str(syllabus["_id"]) if syllabus else None
    syllabus_filename = syllabus.get("filename") if syllabus else None

    # Check if plan exists
    plan_doc = load_plan(user_id)
    has_plan = plan_doc is not None

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "user_name": request.session.get("user_name"),
            "avg_familiarity": avg_familiarity,
            "learning_speed": learning_speed,
            "syllabus_id": syllabus_id,
            "syllabus_filename": syllabus_filename,
            "has_plan": has_plan
        }
    )


# ⭐ FIX: /upload route REMOVED from here.
# It is defined in app/routes/syllabus.py only.
# Having it in both files caused silent route conflict.


@router.get("/plans", response_class=HTMLResponse)
def study_plans(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plans",
            "schedule": None,
            "confidence": None,
            "meta": None,
            "syllabus_id": None
        }
    )


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "active_page": "profile",
            "user_name": request.session.get("user_name"),
            "user_email": request.session.get("user_email")
        }
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)