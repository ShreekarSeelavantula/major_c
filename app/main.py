from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import auth, pages

app = FastAPI(title="AI Study Planner")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routes
app.include_router(pages.router)
app.include_router(auth.router)   # ❌ NO prefix here
