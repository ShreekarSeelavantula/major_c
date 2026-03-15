def update_topic_familiarity(topic_state, new_score):

    attempts = topic_state.get("attempts", 0)
    old_familiarity = topic_state.get("familiarity", 0)

    updated = (
        old_familiarity * attempts + new_score
    ) / (attempts + 1)

    topic_state["familiarity"] = round(updated, 3)
    topic_state["confidence"] = topic_state["familiarity"]
    topic_state["attempts"] = attempts + 1

    return topic_state

def update_familiarity(learner_state, topic_scores):

    if "topic_states" not in learner_state:
        learner_state["topic_states"] = {}

    for topic, score in topic_scores.items():

        topic_state = learner_state["topic_states"].get(topic)

        if not topic_state:
            topic_state = {
                "familiarity": 0,
                "confidence": 0,
                "attempts": 0
            }

        topic_state = update_topic_familiarity(
            topic_state,
            score
        )

        learner_state["topic_states"][topic] = topic_state

    return learner_state