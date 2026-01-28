from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from fastapi.responses import RedirectResponse
from bson import ObjectId

from app.database import fs, syllabus_collection

router = APIRouter(tags=["Syllabus"])

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png"
}

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload_syllabus(
    request: Request,
    file: UploadFile = File(...)
):
    # 1️⃣ Auth check
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 2️⃣ File type validation
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, PNG files allowed"
        )

    # 3️⃣ Read file
    contents = await file.read()

    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds 10MB limit"
        )

    # 4️⃣ Store file in GridFS
    file_id = fs.put(
        contents,
        filename=file.filename,
        content_type=file.content_type,
        metadata={"user_id": user_id}
    )

    # 5️⃣ Store metadata
    syllabus_collection.insert_one({
        "user_id": ObjectId(user_id),
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "status": "uploaded"
    })

    # 6️⃣ Redirect
    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER
    )
