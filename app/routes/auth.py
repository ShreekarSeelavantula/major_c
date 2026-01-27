from fastapi import APIRouter, HTTPException, Form, status
from fastapi.responses import RedirectResponse
from app.database import users_collection
from app.utils.security import hash_password, verify_password
import re

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------- Helpers ----------
def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def is_valid_phone(phone: str) -> bool:
    return phone.isdigit() and len(phone) == 10


# ---------- SIGNUP ----------
@router.post("/signup")
def signup(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    degree: str = Form(...),
    branch: str = Form(None),
    year: int = Form(...),
    study_preference: str = Form(None),
):
    # 1️⃣ Basic validations
    if len(name.strip()) < 3:
        raise HTTPException(status_code=400, detail="Name too short")

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="Phone must be 10 digits")

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    # 2️⃣ Duplicate checks
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    if users_collection.find_one({"phone": phone}):
        raise HTTPException(status_code=400, detail="Phone already registered")

    # 3️⃣ Insert user
    users_collection.insert_one({
        "name": name.strip(),
        "email": email.lower(),
        "phone": phone,
        "hashed_password": hash_password(password[:72]),  # bcrypt safe
        "degree": degree,
        "branch": branch,
        "year": year,
        "study_preference": study_preference,
        "is_active": True,
        "created_at": None   # later we’ll use datetime
    })

    # 4️⃣ Redirect to login
    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ---------- LOGIN ----------
@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...)
):
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")

    db_user = users_collection.find_one({"email": email.lower()})

    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(password[:72], db_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if not db_user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ---------- DEBUG / DB CHECK ----------
@router.get("/force-db")
def force_db():
    users_collection.insert_one({
        "name": "Debug User",
        "email": "debug@test.com",
        "phone": "9999999999",
        "hashed_password": "debug",
        "degree": "B.Tech",
        "year": 4,
        "is_active": True
    })
    return {"status": "MongoDB working, test document inserted"}
