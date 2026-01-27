from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import auth, pages

app = FastAPI(title="AI Study Planner")

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Page routes (/, /signup, /login, /dashboard)
app.include_router(pages.router)

# Auth routes (/auth/signup, /auth/login)
app.include_router(auth.router)
