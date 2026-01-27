from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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


# ---------------- Dashboard Pages ---------------- #

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


@router.get("/upload", response_class=HTMLResponse)
def upload_syllabus(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


@router.get("/plans", response_class=HTMLResponse)
def study_plans(request: Request):
    return templates.TemplateResponse(
        "plans.html",
        {"request": request}
    )


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    return templates.TemplateResponse(
        "profile.html",
        {"request": request}
    )


@router.get("/logout")
def logout():
    # Session cleanup will be added later
    return RedirectResponse(url="/login", status_code=303)
