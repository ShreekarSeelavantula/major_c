from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import fs, syllabus_collection
from app.services.syllabus_parser import extract_text_from_pdf
from app.services.ocr_service import extract_text_with_ocr
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus

from app.services.subject_detector import detect_subjects

from fastapi import Form

from app.services.syllabus_pipeline import process_syllabus


router = APIRouter(tags=["Syllabus"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png"
}

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


# --------------------------------------------------
# Upload Page
# --------------------------------------------------
@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("upload.html", {"request": request})


# --------------------------------------------------
# Upload Handler (PREVIEW ONLY)
# --------------------------------------------------
@router.post("/upload")
async def upload_syllabus(
    request: Request,
    file: UploadFile = File(...)
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG allowed")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    # Store file in GridFS
    file_id = fs.put(
        contents,
        filename=file.filename,
        content_type=file.content_type,
        metadata={"user_id": user_id}
    )

    # -------- PREVIEW EXTRACTION (FIRST 3 PAGES ONLY) --------
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
# Validate Syllabus (USER ACTION)
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

    # ---- FULL TEXT EXTRACTION ----
    file_bytes = fs.get(syllabus["file_id"]).read()
    full_text = extract_text_from_pdf(file_bytes)

    # ---- DETECT SUBJECTS ----
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
# Full Extraction + Structuring (CORE STEP)
# --------------------------------------------------
@router.get("/syllabus/extract-full/{syllabus_id}")
def extract_full_syllabus(request: Request, syllabus_id: str):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    # ---- FULL TEXT EXTRACTION ----
    file_bytes = fs.get(syllabus["file_id"]).read()
    full_text = extract_text_from_pdf(file_bytes)

    # ---- STRUCTURE FULL SYLLABUS ----
    structured_units = structure_syllabus(full_text)

    structured_payload = [
        {
            "unit_number": unit.unit_number,
            "title": unit.title,
            "topics": [topic.title for topic in unit.topics]
        }
        for unit in structured_units
    ]

    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {
            "$set": {
                "full_text": full_text,
                "structured_syllabus": structured_payload,
                "status": "structured"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )
    

@router.post("/syllabus/structure/{syllabus_id}")
def structure_selected_subject(
    request: Request,
    syllabus_id: str,
    subject_text: str = Form(...)
):

    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    structured_units = structure_syllabus(subject_text)


    enriched_topics = process_syllabus(structured_units)

    # Map enriched data by topic name
    enriched_map = {
        t["topic"]: t for t in enriched_topics
    }

    structured_payload = []

    for unit in structured_units:
        unit_topics = []

        for topic in unit.topics:
            name = topic.title
            enriched = enriched_map.get(name)

            if enriched:
                unit_topics.append({
                    "name": name,
                    "complexity": enriched["complexity"],
                    "score": enriched["score"],
                    "estimated_hours": enriched["estimated_hours"],
                    "unit_index": unit.unit_number
                })

        structured_payload.append({
            "unit_number": unit.unit_number,
            "title": unit.title,
            "topics": unit_topics
        })


    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {
            "$set": {
                "structured_syllabus": structured_payload,
                "selected_subject": subject_text,
                "status": "structured"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


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
                "status": "subjects_detected"
            }
        }
    )

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

