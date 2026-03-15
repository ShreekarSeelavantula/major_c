import random

class DiagnosticService:

    def generate_questions(self, topics):
        """
        Generate simple MCQs for diagnostic familiarity testing.
        For v1 we use rule-based templates.
        Later this can be replaced with AI generation.
        """

        question_bank = {
            "Normalization": {
                "question": "Which normal form removes transitive dependency?",
                "options": ["1NF", "2NF", "3NF", "BCNF"],
                "answer": "3NF"
            },
            "ER Model": {
                "question": "What does ER stand for in ER model?",
                "options": [
                    "Entity Relationship",
                    "Extended Relation",
                    "Entity Representation",
                    "External Relation"
                ],
                "answer": "Entity Relationship"
            },
            "Transactions": {
                "question": "Which property ensures all operations succeed or fail together?",
                "options": ["Atomicity", "Consistency", "Isolation", "Durability"],
                "answer": "Atomicity"
            }
        }

        questions = []

        for topic in topics:
            if topic in question_bank:
                q = question_bank[topic]

                questions.append({
                    "topic": topic,
                    "question": q["question"],
                    "options": q["options"],
                    "answer": q["answer"]
                })

        return questions


    def evaluate_answers(self, questions, user_answers):
        """
        Calculate familiarity score based on answers.
        """

        topic_scores = {}

        for q in questions:
            topic = q["topic"]
            correct_answer = q["answer"]

            user_answer = user_answers.get(topic)

            if topic not in topic_scores:
                topic_scores[topic] = {
                    "correct": 0,
                    "total": 0
                }

            topic_scores[topic]["total"] += 1

            if user_answer == correct_answer:
                topic_scores[topic]["correct"] += 1


        familiarity_scores = {}

        for topic, score in topic_scores.items():

            familiarity = score["correct"] / score["total"]

            familiarity_scores[topic] = {
                "familiarity": round(familiarity, 2),
                "confidence": 0.3,
                "attempts": score["total"]
            }

        return familiarity_scores