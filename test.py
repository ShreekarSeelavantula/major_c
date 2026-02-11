from app.database import syllabus_collection
from app.services.subject_detector import detect_subjects

# Get latest structured syllabus document
doc = syllabus_collection.find_one(
    {},
    sort=[("_id", -1)]
)

if not doc:
    print("No syllabus found in DB")
    exit()

full_text = doc.get("full_text")

if not full_text:
    print("Full text not extracted yet")
    exit()

subjects = detect_subjects(full_text)

print("\n========== DETECTED SUBJECTS ==========\n")

for s in subjects:
    print("Code:", s["course_code"])
    print("Title:", s["title"])
    print("Text length:", len(s["text"]))
    print("-" * 40)
