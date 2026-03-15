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
    def generate_mcqs(topic, num_questions=3):

        prompt = f"""
You are an exam question generator.

Generate {num_questions} multiple choice questions about:

TOPIC: {topic}

Rules:
- 4 options per question
- Only one correct answer
- Answer must exactly match one option
- No explanations
- Return ONLY JSON array

Format:

[
 {{
  "question": "text",
  "options": ["A","B","C","D"],
  "answer": "A"
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

            return questions

        except Exception as e:
            raise Exception(f"AI Question Generation Failed: {str(e)}")