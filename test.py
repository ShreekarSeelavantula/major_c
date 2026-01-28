from app.services.syllabus_pipeline import process_syllabus
from app.services.syllabus_structurer import structure_syllabus

text = """
UNIT I
Introduction to DBMS
Normalization techniques
"""

structured = structure_syllabus(text)
output = process_syllabus(structured)

for o in output:
    print(o)
