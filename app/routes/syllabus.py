from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import fs, syllabus_collection
from app.services.syllabus_parser import extract_text_from_pdf
from app.services.ocr_service import extract_text_with_ocr
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus

router = APIRouter(tags=["Syllabus"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png"
}

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


# -----------------------------
# Upload Page
# -----------------------------
@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


# -----------------------------
# Upload Handler
# -----------------------------
@router.post("/upload")
async def upload_syllabus(
    request: Request,
    file: UploadFile = File(...)
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, PNG allowed"
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds 10MB limit"
        )

    # Store file in GridFS
    file_id = fs.put(
        contents,
        filename=file.filename,
        content_type=file.content_type,
        metadata={"user_id": user_id}
    )

    extracted_text = ""
    status_value = "uploaded"

    if file.content_type == "application/pdf":
        extracted_text = extract_text_from_pdf(contents)

        if not extracted_text or len(extracted_text.strip()) < 50:
            extracted_text = extract_text_with_ocr(contents)
            status_value = "parsed_with_ocr"
        else:
            status_value = "parsed"

    # -----------------------------
    # Intelligent syllabus analysis
    # -----------------------------
    analysis = analyze_syllabus(extracted_text)

    if not analysis["is_syllabus"]:
        raise HTTPException(
            status_code=400,
            detail="Uploaded document does not appear to be a syllabus"
        )

    if analysis["has_multiple_subjects"]:
        final_status = "awaiting_subject_selection"
    else:
        final_status = "ready_for_structuring"

    result = syllabus_collection.insert_one({
        "user_id": ObjectId(user_id),
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "status": final_status,
        "analysis": analysis,
        "subjects_detected": analysis.get("subjects", []),
        "selected_subject": None,
        "extracted_text": extracted_text,
        "structured_syllabus": None
    })

    syllabus_id = str(result.inserted_id)

    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# -----------------------------
# Preview Page
# -----------------------------
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
            "filename": syllabus["filename"],
            "status": syllabus["status"],
            "subjects": syllabus.get("subjects_detected", []),
            "analysis": syllabus.get("analysis", {})
        }
    )


# -----------------------------
# Subject Selection Handler
# -----------------------------
@router.post("/syllabus/select-subject")
def select_subject(
    request: Request,
    syllabus_id: str = Form(...),
    selected_subject: str = Form(...)
):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    syllabus = syllabus_collection.find_one({
        "_id": ObjectId(syllabus_id),
        "user_id": ObjectId(request.session["user_id"])
    })

    if not syllabus:
        raise HTTPException(status_code=404, detail="Syllabus not found")

    full_text = syllabus.get("extracted_text", "")
    subjects = syllabus.get("subjects_detected", [])

    lines = full_text.splitlines()
    collected = []
    capture = False

    for line in lines:
        if selected_subject.lower() in line.lower():
            capture = True

        if capture:
            collected.append(line)

        if capture:
            for s in subjects:
                if s != selected_subject and s.lower() in line.lower():
                    capture = False
                    break

    subject_text = "\n".join(collected).strip()

    if len(subject_text) < 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to isolate subject syllabus"
        )

    structured_units = structure_syllabus(subject_text)

    syllabus_collection.update_one(
        {"_id": ObjectId(syllabus_id)},
        {"$set": {
            "selected_subject": selected_subject,
            "structured_syllabus": [u.dict() for u in structured_units],
            "status": "ready_for_structuring"
        }}
    )

    return RedirectResponse(
        url=f"/plan/configure/{syllabus_id}",
        status_code=303
    )
