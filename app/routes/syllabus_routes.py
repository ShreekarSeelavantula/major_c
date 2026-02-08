from fastapi import APIRouter, UploadFile, File
from app.services.text_extractor import extract_text
from app.services.syllabus_validator import analyze_syllabus
from app.services.syllabus_structurer import structure_syllabus

router = APIRouter(prefix="/syllabus")

@router.post("/validate")
async def validate_syllabus(file: UploadFile = File(...)):
    text = extract_text(file)

    validation = analyze_syllabus(text)
    if not validation["is_syllabus"]:
        return {
            "valid": False,
            "reason": validation["reason"]
        }

    units = structure_syllabus(text)

    return {
        "valid": True,
        "units": units
    }
