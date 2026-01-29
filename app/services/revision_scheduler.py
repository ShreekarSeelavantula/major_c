from typing import List
from app.models.learner_state import LearnerTopicState


def get_revision_topics(
    learner_topics: List[LearnerTopicState],
    daily_limit: int = 5
) -> List[LearnerTopicState]:
    """
    Returns a prioritized list of topics that need revision
    """

    revision_candidates = [
        t for t in learner_topics
        if t.revision_due
    ]

    # ---------- Priority Rules ----------
    # 1. Lowest retention first
    # 2. More attempts = higher importance
    revision_candidates.sort(
        key=lambda t: (t.retention_score, -t.attempts)
    )

    return revision_candidates[:daily_limit]
