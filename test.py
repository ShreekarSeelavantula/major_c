from app.services.syllabus_pipeline import process_syllabus

structured = [
    {
        "topics": [
            {"title": "Introduction to DBMS"},
            {"title": "Explain database and DBMS concepts"}
        ]
    },
    {
        "topics": [
            {"title": "Normalization"},
            {"title": "Analyze normalization techniques"}
        ]
    }
]

output = process_syllabus(structured)

for o in output:
    print(o)
