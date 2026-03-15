from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth
from app.routes import pages
from app.routes import syllabus
from app.routes import planner
from app.routes import familiarity_test
from app.routes import plan
from app.routes import diagnostic
from app.routes import progress

# --------------------------------------------------
# 1. Create app
# --------------------------------------------------
app = FastAPI(title="Prep Genie | AI Study Planner")

# --------------------------------------------------
# 2. Session middleware
# --------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key="prepgenie-secret-key",   # move to .env in production
    max_age=60 * 60 * 24                 # 1 day
)

# --------------------------------------------------
# 3. Static files
# --------------------------------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --------------------------------------------------
# 4. Routes
# --------------------------------------------------

# Public pages (home, login, signup, dashboard, profile)
app.include_router(pages.router)

# Auth (signup, login, logout)
app.include_router(auth.router)

# Syllabus (upload, preview, validate, structure, plan view)
app.include_router(syllabus.router)

# Familiarity test (initial, micro, self-rating, submit, result)
app.include_router(familiarity_test.router)

# Adaptive plan (configure, generate, view)
app.include_router(plan.router)

# Planner API (direct JSON endpoint for testing)
app.include_router(planner.router)

# Diagnostic service (rule-based question generation)
app.include_router(diagnostic.router)

# Daily progress tracker (today's tasks, mark done, auto regenerate)
app.include_router(progress.router)


# --------------------------------------------------
# 5. Error handlers
# --------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    with open("app/templates/404.html") as f:
        content = f.read()
    return HTMLResponse(content=content, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    with open("app/templates/500.html") as f:
        content = f.read()
    return HTMLResponse(content=content, status_code=500)