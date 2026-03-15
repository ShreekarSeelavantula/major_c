import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class AIQuestionGenerator:

    @staticmethod
    def _extract_json(text):
        """
        Safely extract JSON array from Groq response
        """

        # Remove markdown code blocks if present
        text = re.sub(r"```json", "", text)
        text = re.sub(r"```", "", text)

        # Extract JSON array using regex
        match = re.search(r"\[.*\]", text, re.DOTALL)

        if not match:
            raise Exception("AI returned no valid JSON array")

        json_text = match.group(0)

        return json.loads(json_text)

    @staticmethod
    def _resolve_answer(answer, options):
        """
        Ensure the answer is always the full option text.

        Handles two cases the AI might return:
          - A single letter:  "A", "B", "C", "D"
          - Full option text: "Employee well-being and productivity"
        """

        answer = answer.strip()

        # ⭐ FIX: use `in list` not `in string` to avoid substring false-positives.
        # "AB" in "ABCD"  → True  (WRONG — substring match)
        # "AB" in ["A","B","C","D"] → False (CORRECT — membership check)
        is_letter = len(answer) == 1 and answer.upper() in ["A", "B", "C", "D"]

        if is_letter:
            idx = ord(answer.upper()) - ord("A")
            if 0 <= idx < len(options):
                return options[idx].strip()

        return answer

    @staticmethod
    def generate_mcqs(topic, num_questions=3, domain=""):
        """
        Generate MCQs for a given topic.

        Args:
            topic:         The specific topic name
            num_questions: How many questions to generate
            domain:        Subject/course name for context
                           (e.g. "Organizational Behaviour").
                           Prevents AI from generating off-topic questions.
        """

        domain_context = (
            f"This topic belongs to the subject: {domain}.\n"
            if domain else ""
        )

        prompt = f"""
You are an exam question generator.

{domain_context}Generate {num_questions} multiple choice questions about:

TOPIC: {topic}

Rules:
- Questions must be specifically about {topic} in the context of {domain or "the subject"}
- 4 options per question (plain text, NO letter prefixes like A) B) etc.)
- Only one correct answer
- The "answer" field must be the EXACT full text of the correct option
- No explanations
- Return ONLY a JSON array, no markdown, no extra text

Format:

[
 {{
  "question": "Question text here?",
  "options": ["Option one", "Option two", "Option three", "Option four"],
  "answer": "Option one"
 }}
]
"""

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Groq API HTTP Error: {response.text}")

            data = response.json()

            if "choices" not in data:
                raise Exception(f"Groq API Format Error: {data}")

            content = data["choices"][0]["message"]["content"]

            questions = AIQuestionGenerator._extract_json(content)

            if not isinstance(questions, list):
                raise Exception("AI response is not a list")

            # Normalise every question's answer to full option text
            for q in questions:
                q["answer"] = AIQuestionGenerator._resolve_answer(
                    q.get("answer", ""),
                    q.get("options", [])
                )

            return questions

        except Exception as e:
            raise Exception(f"AI Question Generation Failed: {str(e)}")