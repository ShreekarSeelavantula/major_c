from datetime import datetime
from bson import ObjectId


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
        "status": "uploaded",  # uploaded | parsed | assessed
        "uploaded_at": datetime.utcnow()
    }
