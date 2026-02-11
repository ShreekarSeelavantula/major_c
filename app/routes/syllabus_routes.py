from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.text_extractor import extract_text
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus

from app.services.subject_detector import detect_subjects

from fastapi import Form


router = APIRouter(prefix="/syllabus")
templates = Jinja2Templates(directory="app/templates")




@router.post("/validate/{syllabus_id}", response_class=HTMLResponse)
async def validate_syllabus(request: Request, syllabus_id: str):

    extracted_text = request.session.get("extracted_text")
    filename = request.session.get("filename")

    if not extracted_text:
        return templates.TemplateResponse(
            "syllabus_preview.html",
            {
                "request": request,
                "syllabus": {
                    "filename": filename,
                    "preview_text": "",
                    "validated": False,
                    "error": "No extracted text found."
                }
            }
        )

    validation = analyze_syllabus(extracted_text)

    if not validation["is_syllabus"]:
        return templates.TemplateResponse(
            "syllabus_preview.html",
            {
                "request": request,
                "syllabus": {
                    "filename": filename,
                    "preview_text": extracted_text[:3000],
                    "validated": False,
                    "error": validation["reason"]
                }
            }
        )

    # ✅ NEW LOGIC: Detect subjects instead of structuring immediately
    subjects = detect_subjects(extracted_text)

    return templates.TemplateResponse(
        "syllabus_preview.html",
        {
            "request": request,
            "syllabus": {
                "filename": filename,
                "preview_text": extracted_text[:3000],
                "validated": True,
                "subjects": subjects,
                "structured": None
            }
        }
    )


@router.post("/structure", response_class=HTMLResponse)
async def structure_subject(request: Request, subject_text: str = Form(...)):

    filename = request.session.get("filename")

    # Call your existing structurer
    structured = structure_syllabus(subject_text)

    return templates.TemplateResponse(
        "syllabus_preview.html",
        {
            "request": request,
            "syllabus": {
                "filename": filename,
                "preview_text": subject_text[:3000],
                "validated": True,
                "subjects": None,
                "structured": structured
            }
        }
    )
