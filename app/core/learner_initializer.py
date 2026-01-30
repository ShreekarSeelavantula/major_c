from typing import List, Dict
from app.models.learner_state import LearnerTopicState
from datetime import datetime


def initialize_learner_state(
    topics: List[dict],
    familiarity_scores: Dict[str, float] | None = None
) -> Dict[str, LearnerTopicState]:
    """
    topics: output of syllabus_pipeline
    familiarity_scores: optional dict { topic_title: score (0.0 - 1.0) }

    returns:
        dict { topic_id: LearnerTopicState }
    """

    learner_state = {}
    familiarity_scores = familiarity_scores or {}

    for topic in topics:
        topic_id = topic["topic"]

        familiarity = familiarity_scores.get(topic_id, 0.0)

        learner_state[topic_id] = LearnerTopicState(
            topic_id=topic_id,
            familiarity=familiarity,
            confidence=familiarity,  # initial confidence mirrors familiarity
            learning_speed=1.0,
            retention_score=0.5,
            attempts=0,
            last_studied=None,
            revision_due=False
        )

    return learner_state
