from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import fs, syllabus_collection
from app.services.syllabus_parser import extract_text_from_pdf
from app.services.ocr_service import extract_text_with_ocr
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus
from app.services.subject_detector import detect_subjects
from app.services.syllabus_pipeline import process_syllabus

# ✅ NEW
from app.services.planner_service import PlannerService

from app.services.topic_complexity_engine import evaluate_topic



router = APIRouter(tags=["Syllabus"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png"
}

MAX_SIZE = 10 * 1024 * 1024


# --------------------------------------------------
# Upload Page
# --------------------------------------------------
@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("upload.html", {"request": request})


# --------------------------------------------------
# Upload Handler
# --------------------------------------------------
@router.post("/upload")
async def upload_syllabus(request: Request, file: UploadFile = File(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG allowed")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    file_id = fs.put(
        contents,
        filename=file.filename,
        content_type=file.content_type,
        metadata={"user_id": user_id}
    )

    preview_text = ""

    if file.content_type == "application/pdf":
        preview_text = extract_text_from_pdf(contents, max_pages=3)

        if not preview_text or len(preview_text.strip()) < 50:
            preview_text = extract_text_with_ocr(contents)

    syllabus_id = syllabus_collection.insert_one({
        "user_id": ObjectId(user_id),
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "preview_text": preview_text,
        "full_text": None,
        "validated": False,
        "subjects_detected": [],
        "selected_subject": None,
        "structured_syllabus": None,
        "generated_plan": None,   # ✅ NEW
        "status": "preview"
    }).inserted_id

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# --------------------------------------------------
# Preview Page
# --------------------------------------------------
@router.get("/syllabus/preview/{syllabus_id}", response_class=HTMLResponse)
def preview_syllabus(request: Request, syllabus_id: str):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    return templates.TemplateResponse(
        "syllabus_preview.html",
        {
            "request": request,
            "syllabus": syllabus
        }
    )


# --------------------------------------------------
# Validate
# --------------------------------------------------
@router.post("/syllabus/validate/{syllabus_id}")
def validate_syllabus(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    analysis = analyze_syllabus(syllabus["preview_text"])

    if not analysis["is_syllabus"]:
        raise HTTPException(status_code=400, detail=analysis["reason"])

    file_bytes = fs.get(syllabus["file_id"]).read()
    full_text = extract_text_from_pdf(file_bytes)

    subjects = detect_subjects(full_text)

    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {
            "$set": {
                "validated": True,
                "full_text": full_text,
                "subjects_detected": subjects,
                "status": "subjects_detected"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# --------------------------------------------------
# STRUCTURE + GENERATE PLAN (UPDATED CORE)
# --------------------------------------------------
@router.post("/syllabus/structure/{syllabus_id}")
def structure_selected_subject(
    request: Request,
    syllabus_id: str,
    subject_text: str = Form(...)
):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    structured_units = structure_syllabus(subject_text)

    # -------- STORE STRUCTURED --------
    structured_payload = []
    planner_topics = []

    for unit in structured_units:
        unit_topics = []

        for index, topic in enumerate(unit.topics):
            name = topic.title

            # Extract subtopics if available
            subtopics = []
            if hasattr(topic, "subtopics"):
                subtopics = topic.subtopics

            # 🔥 Evaluate Complexity (Single Source of Truth)
            complexity_data = evaluate_topic(
                topic_title=name,
                subtopics=subtopics,
                topic_index=index
            )

            # Simple estimated hours formula
            estimated_hours = max(1, complexity_data["total_score"] // 2)

            # -------- STRUCTURED PAYLOAD --------
            unit_topics.append({
                "name": name,
                "subtopics": subtopics,
                "complexity": complexity_data,
                "score": complexity_data["total_score"],
                "estimated_hours": estimated_hours,
                "unit_index": unit.unit_number
            })

            # -------- PLANNER INPUT --------
            planner_topics.append({
                "topic": name,
                "complexity": complexity_data["difficulty"],
                "estimated_hours": estimated_hours
            })

        structured_payload.append({
            "unit_number": unit.unit_number,
            "title": unit.title,
            "topics": unit_topics
        })

    # -------- GENERATE PLAN --------
    learner_state = {
        "learning_speed": 1.0,
        "consistency": 1.0,
        "topic_states": {}
    }

    generated_plan = PlannerService.create_plan(
        topics=planner_topics,
        learner_state=learner_state,
        hours_per_day=3,
        deadline_days=7
    )

    # -------- UPDATE DB --------
    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {
            "$set": {
                "structured_syllabus": structured_payload,
                "selected_subject": subject_text,
                "generated_plan": generated_plan,
                "status": "structured"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# --------------------------------------------------
# CHANGE SUBJECT
# --------------------------------------------------
@router.get("/syllabus/change-subject/{syllabus_id}")
def change_subject(request: Request, syllabus_id: str):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {
            "$set": {
                "structured_syllabus": None,
                "selected_subject": None,
                "generated_plan": None,   # ✅ important (new field)
                "status": "subjects_detected"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )
