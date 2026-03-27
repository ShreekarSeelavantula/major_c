import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


# -------------------------------------------------------
# GENERIC WORD FILTER
# Topics extracted from syllabuses often contain single
# generic academic words that mean nothing in isolation.
# e.g. "Definition", "Types", "Labor", "Emotional"
# These pass the AI cleaner because they are valid English
# words — but they are useless as study topics.
# This filter rejects them before they get saved.
# -------------------------------------------------------

GENERIC_WORDS = {
    "definition", "definitions",
    "types", "type",
    "introduction", "intro",
    "overview", "summary",
    "basics", "basic",
    "concepts", "concept",
    "labor", "labour",
    "emotional", "intelligence",
    "management", "intervention",
    "theories", "theory",
    "framework", "frameworks",
    "nature", "scope",
    "importance", "need",
    "effects", "effect",
    "characteristics", "characteristic",
    "components", "component",
    "elements", "element",
    "factors", "factor",
    "principles", "principle",
    "objectives", "objective",
    "functions", "function",
    "applications", "application",
    "advantages", "disadvantages",
    "features", "feature",
    "methods", "method",
    "techniques", "technique",
    "process", "processes",
    "model", "models",
    "structure", "structures",
    "system", "systems",
    "review", "analysis",
    "classification", "categories",
    "comparison", "examples",
}


def _is_generic(name: str) -> bool:
    """
    Returns True if the topic name is a single generic word
    that has no meaning as a standalone study topic.

    Rules:
    - If it is a single word AND that word is in GENERIC_WORDS -> reject
    - If it is two words and BOTH are in GENERIC_WORDS -> reject
    - Otherwise keep it (multi-word topics are almost always fine)
    """
    cleaned = name.strip().lower()
    words = cleaned.split()

    if len(words) == 1 and cleaned in GENERIC_WORDS:
        return True

    if len(words) == 2 and all(w in GENERIC_WORDS for w in words):
        return True

    return False


class TopicCleaner:

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    MODEL = "llama-3.1-8b-instant"

    @staticmethod
    def clean_topics(structured_syllabus):

        print("Calling Groq API for topic cleaning...")

        # --------------------------------
        # Extract ONLY topic names
        # --------------------------------
        topic_names = []

        for unit in structured_syllabus:
            for topic in unit["topics"]:
                topic_names.append(topic["name"])

        # --------------------------------
        # Prompt
        # --------------------------------
        prompt = f"""
You are cleaning syllabus topic names extracted from a PDF.

The extraction may contain:
- broken words
- duplicates
- meaningless words like "definition"
- poor capitalization
- merged topics

Clean and normalize the topic names.

Rules:
- Keep the meaning academic
- Fix capitalization
- Merge broken words
- Remove duplicates
- Expand incomplete names if needed

Return ONLY a JSON array.

Example output:

[
"Introduction to Organizational Behaviour",
"Nature and Scope of Organizational Behaviour",
"Personality Theories"
]

You are cleaning topic names extracted from a syllabus.

Your job is ONLY to clean the wording of the existing topic.

You must NOT introduce new concepts.
You must NOT change the academic meaning.
You must NOT reorder topics.
You must NOT merge units.

You may only:
- fix spelling
- fix capitalization
- remove meaningless filler words
- split merged topics if they appear in one line

VERY IMPORTANT:
The cleaned topic must keep the SAME meaning as the original.

--------------------------------
EXAMPLES
--------------------------------

Example 1

Input:
"definition"

Output:
"Definition"

Reason:
Only capitalization fixed.

--------------------------------

Example 2

Input:
"Frame work"

Output:
"Framework"

Reason:
Spelling corrected.

--------------------------------

Example 3

Input:
"Organizational behaviour models."

Output:
"Organizational Behavior Models"

Reason:
Removed punctuation and fixed capitalization.

--------------------------------

Example 4

Input:
"The learning process, Learning theories, Organizational behaviour modification"

Output:
[
"Learning Process",
"Learning Theories",
"Organizational Behavior Modification"
]

Reason:
Split merged topics into separate topics.

--------------------------------

Example 5

Input:
"Organizational behaviour"

Correct Output:
"Organizational Behavior"

WRONG OUTPUT (DO NOT DO THIS):
"Introduction to Organizational Behavior"

Reason:
This changes the meaning.

--------------------------------

Example 6

Input:
"nature and scope of ob"

Output:
"Nature and Scope of Organizational Behavior"

Reason:
Expanded abbreviation but kept the same meaning.

--------------------------------

Follow these rules strictly.
Do NOT invent new topics.
Do NOT reorganize units.
Do NOT summarize.
Do NOT rewrite academically.

Only clean the wording of existing topics.
The number of topics should remain the same unless a single topic clearly contains multiple topics separated by commas.


Return ONLY JSON.

Topic names:

{json.dumps(topic_names)}
"""

        headers = {
            "Authorization": f"Bearer {TopicCleaner.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": TopicCleaner.MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        response = requests.post(
            TopicCleaner.API_URL,
            headers=headers,
            json=payload
        )

        print("Groq response:", response.text)

        try:

            data = response.json()

            content = data["choices"][0]["message"]["content"]

            # Remove markdown
            content = content.replace("```json", "").replace("```python", "").replace("```", "").strip()

            # Extract JSON array
            json_start = content.find("[")
            json_end = content.find("]") + 1

            cleaned_list = json.loads(content[json_start:json_end])

            print("Cleaned topic list:", cleaned_list)

            # -------------------------------------------------------
            # Write cleaned names back into structured syllabus.
            # FILTER: skip generic single words before saving.
            # If a cleaned name is generic (e.g. "Labor", "Types"),
            # keep the original name instead of replacing it.
            # This prevents meaningless topics polluting the plan.
            # -------------------------------------------------------
            index = 0

            for unit in structured_syllabus:
                for topic in unit["topics"]:

                    if index < len(cleaned_list):
                        candidate = cleaned_list[index]

                        if _is_generic(candidate):
                            # Keep original name — generic word is worse
                            print(f"Skipping generic: '{candidate}' keeping '{topic['name']}'")
                        else:
                            topic["name"] = candidate

                    index += 1

            return structured_syllabus

        except Exception as e:

            print("AI parsing error:", e)

            return structured_syllabus