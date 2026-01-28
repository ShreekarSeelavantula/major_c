from fastapi import APIRouter, HTTPException, Form, status, Request
from fastapi.responses import RedirectResponse
from app.database import users_collection
from app.utils.security import hash_password, verify_password
import re
from datetime import datetime

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
    email = email.lower().strip()

    # Validations
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

    # Duplicate checks
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    if users_collection.find_one({"phone": phone}):
        raise HTTPException(status_code=400, detail="Phone already registered")

    # Insert user
    users_collection.insert_one({
        "name": name.strip(),
        "email": email,
        "phone": phone,
        "hashed_password": hash_password(password[:72]),
        "degree": degree,
        "branch": branch,
        "year": year,
        "study_preference": study_preference,
        "is_active": True,
        "created_at": datetime.utcnow()
    })

    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ---------- LOGIN ----------
@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    email = email.lower().strip()

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")

    db_user = users_collection.find_one({"email": email})

    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(password[:72], db_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if not db_user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    # ✅ Save session
    request.session["user_id"] = str(db_user["_id"])
    request.session["user_email"] = db_user["email"]
    request.session["user_name"] = db_user["name"]

    response = RedirectResponse(
    url="/dashboard",
    status_code=status.HTTP_303_SEE_OTHER
    )

    return response



# ---------- LOGOUT ----------
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ---------- DEBUG ----------
@router.get("/force-db")
def force_db():
    users_collection.insert_one({
        "name": "Debug User",
        "email": "debug@test.com",
        "phone": "9999999999",
        "hashed_password": "debug",
        "degree": "B.Tech",
        "year": 4,
        "is_active": True,
        "created_at": datetime.utcnow()
    })
    return {"status": "MongoDB working"}
