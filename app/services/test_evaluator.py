class TestEvaluator:

    @staticmethod
    def evaluate(questions, answers):

        results = {}
        total_questions = 0
        correct_answers = 0

        for topic, qs in questions.items():

            topic_correct = 0

            for i, q in enumerate(qs):

                key = f"{topic}_{i}"
                total_questions += 1

                if answers.get(key) == q["answer"]:
                    correct_answers += 1
                    topic_correct += 1

            results[topic] = topic_correct / len(qs)

        overall_score = correct_answers / total_questions

        return {
            "topic_scores": results,
            "overall_score": overall_score
        }