import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class AIQuestionGenerator:

    @staticmethod
    def generate_mcqs(topic, num_questions=3):

        prompt = f"""
Generate {num_questions} multiple choice questions about {topic}.

Return STRICT JSON format:

[
 {{
  "question": "question text",
  "options": ["A","B","C","D"],
  "answer": "correct option"
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
            "temperature": 0.3
        }

        response = requests.post(url, headers=headers, json=payload)

        data = response.json()

        if "choices" not in data:
            raise Exception(f"AI API Error: {data}")

        content = data["choices"][0]["message"]["content"]

        return json.loads(content)