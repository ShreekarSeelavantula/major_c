# app/services/subject_detector.py

import re
from typing import List, Dict


SUBJECT_PATTERN = re.compile(
    r'([A-Z]{2,4}\d{3}[A-Z]{2})\s*:\s*(.+)',
    re.MULTILINE
)


def detect_subjects(full_text: str) -> List[Dict]:
    """
    Detect subjects from full syllabus text.

    Returns:
        List of dict:
        [
            {
                "course_code": str,
                "title": str,
                "text": str
            }
        ]
    """

    matches = list(SUBJECT_PATTERN.finditer(full_text))

    subjects = []

    if not matches:
        return subjects

    for i in range(len(matches)):
        start_index = matches[i].start()

        if i + 1 < len(matches):
            end_index = matches[i + 1].start()
        else:
            end_index = len(full_text)

        subject_block = full_text[start_index:end_index].strip()

        course_code = matches[i].group(1).strip()
        title = matches[i].group(2).strip()

        subjects.append({
            "course_code": course_code,
            "title": title,
            "text": subject_block
        })

        # Remove tiny subject blocks (likely table listings)
        subjects = [s for s in subjects if len(s["text"]) > 500]


    return subjects
