from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ---------- Auth Guard ----------
def require_login(request: Request):
    if "user_id" not in request.session:
        return False
    return True


# ---------- Public Pages ----------
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


# ---------- Dashboard Pages ----------
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "user_name": request.session.get("user_name")
        }
    )


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "active_page": "upload"
        }
    )
    


@router.get("/plans", response_class=HTMLResponse)
def study_plans(request: Request):
    if not require_login(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "plans.html",
        {
            "request": request,
            "active_page": "plans"
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
