from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.text_extractor import extract_text
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus

router = APIRouter(prefix="/syllabus")
templates = Jinja2Templates(directory="app/templates")


@router.post("/validate/{syllabus_id}", response_class=HTMLResponse)
async def validate_syllabus(request: Request, syllabus_id: str):
    """
    Validates extracted text and shows structured syllabus preview
    """

    # ⚠️ TEMP: replace this with DB fetch later
    # For now assume text already extracted and stored
    extracted_text = request.session.get("extracted_text")
    filename = request.session.get("filename")

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

    structured = structure_syllabus(extracted_text)

    return templates.TemplateResponse(
        "syllabus_preview.html",
        {
            "request": request,
            "syllabus": {
                "filename": filename,
                "preview_text": extracted_text[:3000],
                "validated": True,
                "structured": structured
            }
        }
    )
