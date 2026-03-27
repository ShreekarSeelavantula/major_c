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

    # Load user from MongoDB for avatar
    from app.database import users_collection as uc
    from bson import ObjectId as ObjId
    user = uc.find_one({"_id": ObjId(user_id)}) or {}

    # Load learner state for stats
    learner_state = load_learner_state(user_id)
    avg_familiarity = None
    learning_speed = None

    if learner_state:
        states = list(learner_state.get("topic_states", {}).values())
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
            "user_avatar": user.get("avatar", "🧑"),
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

    user_id = request.session.get("user_id")

    # Load most recent syllabus for syllabus_id (needed for micro test link)
    syllabus = syllabus_collection.find_one(
        {
            "user_id": ObjectId(user_id),
            "status": "structured"
        },
        sort=[("_id", -1)]
    )
    syllabus_id = str(syllabus["_id"]) if syllabus else None

    # Load real plan data
    plan_doc = load_plan(user_id)

    if not plan_doc:
        return templates.TemplateResponse(
            "plans.html",
            {
                "request": request,
                "active_page": "plans",
                "schedule": None,
                "confidence": None,
                "meta": None,
                "syllabus_id": syllabus_id
            }
        )

    schedule = plan_doc["plan"].get("schedule", {})
    confidence = plan_doc["plan"].get("confidence", 0.5)

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plans",
            "schedule": schedule,
            "confidence": confidence,
            "syllabus_id": syllabus_id,
            "meta": {
                "hours_per_day": plan_doc.get("hours_per_day"),
                "deadline_days": plan_doc.get("deadline_days"),
                "created_at": plan_doc.get("created_at")
            }
        }
    )


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    user_id = request.session.get("user_id")

    # Load full user profile from MongoDB
    from app.database import users_collection
    from bson import ObjectId as ObjId
    user = users_collection.find_one({"_id": ObjId(user_id)})

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "active_page": "profile",
            "user": user or {},
            "user_name": request.session.get("user_name"),
            "user_email": request.session.get("user_email")
        }
    )


@router.post("/profile/update")
async def update_profile(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    user_id = request.session.get("user_id")
    form = await request.form()

    from app.database import users_collection
    from bson import ObjectId as ObjId

    update_data = {}

    if form.get("name"):
        update_data["name"] = form["name"].strip()
    if form.get("phone"):
        update_data["phone"] = form["phone"].strip()
    if form.get("degree"):
        update_data["degree"] = form["degree"]
    if form.get("branch"):
        update_data["branch"] = form["branch"].strip()
    if form.get("year"):
        update_data["year"] = int(form["year"])
    if form.get("study_preference"):
        update_data["study_preference"] = form["study_preference"]
    if form.get("avatar"):
        update_data["avatar"] = form["avatar"]

    if update_data:
        users_collection.update_one(
            {"_id": ObjId(user_id)},
            {"$set": update_data}
        )
        # Update session name if changed
        if "name" in update_data:
            request.session["user_name"] = update_data["name"]

    return RedirectResponse("/profile?updated=1", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)