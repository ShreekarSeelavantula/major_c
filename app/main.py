from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, pages, syllabus
from app.routes import planner
from app.routes import familiarity_test


# ✅ 1. Create app FIRST
app = FastAPI(title="AI Study Planner")

# 🔐 2. Session support
app.add_middleware(
    SessionMiddleware,
    secret_key="prepgenie-secret-key",  # change later
    max_age=60 * 60 * 24  # 1 day
)

# 📁 3. Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 📄 4. Page routes
app.include_router(pages.router)

# 🔐 5. Auth routes
app.include_router(auth.router)

# 📤 6. Syllabus upload routes
app.include_router(syllabus.router)

# 🧠 7. Planner routes (NEW)
app.include_router(planner.router)


# 🧠 Familiarity Test routes
app.include_router(familiarity_test.router)