import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class BulkQuestionGenerator:
    """
    Generates ALL questions for ALL topics in ONE API call.

    Why one call?
    - 100 topics × 1 call each = 100 API calls (wasteful, slow, costly)
    - 100 topics × 1 bulk call = 1 API call (fast, efficient)

    Generated questions are stored in:
    data/question_banks/{syllabus_id}.json

    This bank is reused for:
    - Initial Unit-1 diagnostic test
    - Periodic 10-question micro tests
    - Self-rating confirmation questions
    """

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-8b-instant"
    BANK_PATH = "data/question_banks"

    # -------------------------------------------------------
    # PUBLIC: Generate and store question bank
    # -------------------------------------------------------
    @staticmethod
    def build_question_bank(syllabus_id: str, structured_syllabus: list, domain: str = "") -> dict:
        """
        Main entry point.

        1. Extract all topics from structured syllabus
        2. Decide how many questions per topic based on count
        3. Generate all questions in ONE API call
        4. Store to file
        5. Return bank

        Args:
            syllabus_id:          MongoDB _id of syllabus (used as filename)
            structured_syllabus:  list of units with topics
            domain:               subject name for domain locking

        Returns:
            question_bank dict  { topic_name: [question, ...] }
        """

        # Check if bank already exists — avoid regenerating
        existing = BulkQuestionGenerator.load_question_bank(syllabus_id)
        if existing:
            print(f"Question bank already exists for {syllabus_id}, reusing.")
            return existing

        # Extract all topics grouped by unit
        units_topics = BulkQuestionGenerator._extract_topics_by_unit(
            structured_syllabus
        )

        total_topics = sum(len(t) for t in units_topics.values())

        # Decide questions per topic based on total count
        # Keeps total questions reasonable regardless of syllabus size
        questions_per_topic = BulkQuestionGenerator._decide_questions_per_topic(
            total_topics
        )

        print(f"Total topics: {total_topics}, questions per topic: {questions_per_topic}")

        # Generate all questions in one call
        question_bank = BulkQuestionGenerator._generate_bulk(
            units_topics=units_topics,
            questions_per_topic=questions_per_topic,
            domain=domain
        )

        # Save to file
        BulkQuestionGenerator._save_bank(syllabus_id, question_bank)

        return question_bank

    # -------------------------------------------------------
    # PUBLIC: Load existing bank
    # -------------------------------------------------------
    @staticmethod
    def load_question_bank(syllabus_id: str) -> dict | None:
        path = BulkQuestionGenerator._bank_path(syllabus_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    # -------------------------------------------------------
    # PUBLIC: Get questions for specific topics
    # -------------------------------------------------------
    @staticmethod
    def get_questions_for_topics(syllabus_id: str, topic_names: list) -> dict:
        """
        Fetch questions for a specific list of topics from the bank.
        Used by familiarity test routes instead of calling AI each time.

        Returns: { topic_name: [questions] }
        """
        bank = BulkQuestionGenerator.load_question_bank(syllabus_id)

        if not bank:
            return {}

        return {
            topic: bank[topic]
            for topic in topic_names
            if topic in bank
        }

    # -------------------------------------------------------
    # PRIVATE: Extract topics grouped by unit number
    # -------------------------------------------------------
    @staticmethod
    def _extract_topics_by_unit(structured_syllabus: list) -> dict:
        """
        Returns { unit_number: [topic_name, ...] }
        """
        units = {}
        for unit in structured_syllabus:
            unit_num = unit.get("unit_number", 1)
            topics = [t["name"] for t in unit.get("topics", [])]
            if topics:
                units[unit_num] = topics
        return units

    # -------------------------------------------------------
    # PRIVATE: Decide questions per topic
    # -------------------------------------------------------
    @staticmethod
    def _decide_questions_per_topic(total_topics: int) -> int:
        """
        Scale questions per topic so total stays manageable.

        Total topics → questions per topic:
        ≤ 20  → 3 questions (small syllabus, go deep)
        ≤ 50  → 2 questions
        > 50  → 1 question (large syllabus, stay light)
        """
        if total_topics <= 20:
            return 3
        elif total_topics <= 50:
            return 2
        else:
            return 1

    # -------------------------------------------------------
    # PRIVATE: Single bulk API call
    # -------------------------------------------------------
    @staticmethod
    def _generate_bulk(units_topics: dict, questions_per_topic: int, domain: str) -> dict:
        """
        Sends ONE prompt to Groq with all topics.
        Returns { topic_name: [question, ...] }
        """

        # Build flat topic list preserving unit context
        all_topics = []
        for unit_num, topics in units_topics.items():
            for topic in topics:
                all_topics.append({
                    "unit": unit_num,
                    "topic": topic
                })

        domain_lock = f"""
ACADEMIC SUBJECT: {domain}

This is a university-level theory subject.
All questions MUST strictly belong to: {domain}

Do NOT generate questions from:
- Programming, Software Engineering, Web Development
- Computer Science tools, React, JavaScript, Python
- Any topic outside {domain}

If a topic name is generic like "Framework" or "Definition",
interpret it EXCLUSIVELY within the context of {domain}.

""" if domain else ""

        prompt = f"""
You are a university exam question generator.

{domain_lock}

Generate exactly {questions_per_topic} MCQ(s) for EACH topic listed below.

Rules:
- Questions must be strictly about the topic within the subject context
- 4 plain text options per question — NO letter prefixes like A) B)
- Exactly one correct answer
- "answer" field must be the EXACT full text of the correct option
- No explanations, no extra text
- Return ONLY a valid JSON object

Required format:

{{
  "Topic Name One": [
    {{
      "question": "Question text?",
      "options": ["Option one", "Option two", "Option three", "Option four"],
      "answer": "Option one"
    }}
  ],
  "Topic Name Two": [
    {{
      "question": "Question text?",
      "options": ["Option one", "Option two", "Option three", "Option four"],
      "answer": "Option two"
    }}
  ]
}}

Topics to generate questions for:

{json.dumps([t["topic"] for t in all_topics], indent=2)}
"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": BulkQuestionGenerator.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 8000
        }

        try:
            response = requests.post(
                BulkQuestionGenerator.API_URL,
                headers=headers,
                json=payload,
                timeout=60   # bulk call needs more time
            )

            if response.status_code != 200:
                raise Exception(f"Groq API Error: {response.text}")

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            question_bank = BulkQuestionGenerator._extract_json_object(content)

            # Normalize all answers to full option text
            for topic, questions in question_bank.items():
                for q in questions:
                    q["answer"] = BulkQuestionGenerator._resolve_answer(
                        q.get("answer", ""),
                        q.get("options", [])
                    )

            return question_bank

        except Exception as e:
            print(f"Bulk generation failed: {e}")
            # Return empty bank — fallback will handle per-topic
            return {}

    # -------------------------------------------------------
    # PRIVATE: Extract JSON object from response
    # -------------------------------------------------------
    @staticmethod
    def _extract_json_object(text: str) -> dict:
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)

        # Find outermost { }
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            raise Exception("No JSON object found in response")

        return json.loads(text[start:end])

    # -------------------------------------------------------
    # PRIVATE: Resolve answer letter → full text
    # -------------------------------------------------------
    @staticmethod
    def _resolve_answer(answer: str, options: list) -> str:
        answer = answer.strip()
        is_letter = len(answer) == 1 and answer.upper() in ["A", "B", "C", "D"]
        if is_letter:
            idx = ord(answer.upper()) - ord("A")
            if 0 <= idx < len(options):
                return options[idx].strip()
        return answer

    # -------------------------------------------------------
    # PRIVATE: File helpers
    # -------------------------------------------------------
    @staticmethod
    def _bank_path(syllabus_id: str) -> str:
        os.makedirs(BulkQuestionGenerator.BANK_PATH, exist_ok=True)
        return os.path.join(BulkQuestionGenerator.BANK_PATH, f"{syllabus_id}.json")

    @staticmethod
    def _save_bank(syllabus_id: str, bank: dict):
        path = BulkQuestionGenerator._bank_path(syllabus_id)
        with open(path, "w") as f:
            json.dump(bank, f, indent=2)
        print(f"Question bank saved: {path} ({len(bank)} topics)")