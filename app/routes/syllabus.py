from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.database import fs, syllabus_collection
from app.services.syllabus_parser import extract_text_from_pdf  # ✅ Module B enabled

router = APIRouter(tags=["Syllabus"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png"
}

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------- Upload Page ----------------
@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


# ---------------- Upload Handler ----------------
@router.post("/upload")
async def upload_syllabus(
    request: Request,
    file: UploadFile = File(...)
):
    # 🔐 Auth check
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 📄 File type check
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, PNG files allowed"
        )

    # 📦 Read file
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds 10MB limit"
        )

    # 🗄 Store file in GridFS
    file_id = fs.put(
        contents,
        filename=file.filename,
        content_type=file.content_type,
        metadata={"user_id": user_id}
    )

    # 🧠 Extract text (PDF only for now)
    extracted_text = None
    status_value = "uploaded"

    if file.content_type == "application/pdf":
        extracted_text = extract_text_from_pdf(contents)
        status_value = "parsed" if extracted_text else "uploaded"

    # 🧾 Store metadata + extracted text
    result = syllabus_collection.insert_one({
        "user_id": ObjectId(user_id),
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "status": status_value,
        "extracted_text": extracted_text
    })

    syllabus_id = str(result.inserted_id)

    # 🔁 Redirect to preview
    return RedirectResponse(
        url=f"/syllabus/preview/{syllabus_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ---------------- Preview Page ----------------
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
            "text": syllabus.get("extracted_text", "")
        }
    )
