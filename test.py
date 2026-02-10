from pymongo import MongoClient
from bson import ObjectId
import json

# ---- Mongo Connection (same as database.py) ----
MONGO_URL = "mongodb+srv://dbUser:shreekar1572004@cluster0.4wsqsxc.mongodb.net/study_planner?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client["ai_study_planner"]
syllabus_collection = db["syllabus"]

# ---- Fetch latest syllabus record ----
latest = syllabus_collection.find().sort("_id", -1).limit(1)

for doc in latest:
    print("\n========== LATEST SYLLABUS RECORD ==========\n")

    output = {
        "id": str(doc.get("_id")),
        "filename": doc.get("filename"),
        "status": doc.get("status"),
        "validated": doc.get("validated"),
        "has_full_text": bool(doc.get("full_text")),
        "subjects_detected": doc.get("subjects_detected"),
        "selected_subject": doc.get("selected_subject"),
        "structured_syllabus_preview": []
    }

    structured = doc.get("structured_syllabus") or []

    for unit in structured:
        output["structured_syllabus_preview"].append({
            "unit_number": unit.get("unit_number"),
            "title": unit.get("title"),
            "topics_count": len(unit.get("topics", [])),
            "sample_topics": unit.get("topics", [])[:5]
        })

    print(json.dumps(output, indent=4))

print("\n===========================================\n")
