import json
from app.database import syllabus_collection


def fetch_latest_syllabus():

    doc = syllabus_collection.find_one(
        {},
        sort=[("_id", -1)]
    )

    if not doc:
        print("No syllabus found")
        return

    print("\n========== FULL DOCUMENT ==========\n")

    print(json.dumps(
        doc,
        indent=2,
        default=str
    ))

    structured = doc.get("structured_syllabus")

    print("\n========== STRUCTURED SYLLABUS ==========\n")

    print(json.dumps(
        structured,
        indent=2,
        default=str
    ))


if __name__ == "__main__":
    fetch_latest_syllabus()