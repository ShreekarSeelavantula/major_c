from datetime import datetime
from bson import ObjectId
from typing import Optional
from pydantic import BaseModel, Field


class SyllabusModel(BaseModel):
    user_id: ObjectId
    file_id: ObjectId
    filename: str
    content_type: str

    status: str = "uploaded"  # uploaded | parsing | parsed | failed
    extracted_text: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


def syllabus_document(
    *,
    user_id: ObjectId,
    file_id: ObjectId,
    filename: str,
    content_type: str
):
    return {
        "user_id": user_id,
        "file_id": file_id,
        "filename": filename,
        "content_type": content_type,
        "status": "uploaded",
        "created_at": datetime.utcnow()
    }
