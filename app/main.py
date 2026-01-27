from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


from app.routes import auth, pages

app = FastAPI(title="AI Study Planner")

# 🔐 Session support (required for login → dashboard)
app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-secret-later"
)

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Page routes (/, /signup, /login, /dashboard)
app.include_router(pages.router)

# Auth routes (/auth/signup, /auth/login, /auth/logout)
app.include_router(auth.router)
