from app.core.adaptive_plan_generator import generate_adaptive_plan
from app.core.retention_scheduler import apply_retention_decay


class PlannerService:

    @staticmethod
    def _make_mongo_safe(data):
        """
        Recursively convert all dictionary keys to strings.
        Prevents MongoDB InvalidDocument errors.
        """
        if isinstance(data, dict):
            return {
                str(key): PlannerService._make_mongo_safe(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                PlannerService._make_mongo_safe(item)
                for item in data
            ]
        else:
            return data

    @staticmethod
    def create_plan(
        topics,
        learner_state,
        hours_per_day,
        deadline_days,
        topic_order: str = "priority",
        year_pace_multiplier: float = 1.0
    ):
        """
        High-level planner interface.

        Args:
            topics:               list of topic dicts
            learner_state:        full learner state dict
            hours_per_day:        daily study hours
            deadline_days:        days until exam
            topic_order:          "hard_first" | "easy_first" | "priority"
            year_pace_multiplier: float — 1.2 for Year 1-2, 0.9 for Year 3-4
        """

        # Step 1: Apply retention decay
        learner_state = apply_retention_decay(learner_state)

        # Step 2: Generate plan with profile params
        plan = generate_adaptive_plan(
            topics,
            learner_state,
            hours_per_day,
            deadline_days,
            topic_order=topic_order,
            year_pace_multiplier=year_pace_multiplier
        )

        # Step 3: Make Mongo-safe
        safe_plan = PlannerService._make_mongo_safe(plan)

        return safe_plan