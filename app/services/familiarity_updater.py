def update_familiarity(learner_state, topic_scores):

    for topic, score in topic_scores.items():

        topic_state = learner_state["topic_states"].get(topic)

        if not topic_state:
            continue

        topic_state["familiarity"] = score
        topic_state["confidence"] = score
        topic_state["attempts"] += 1

    return learner_state