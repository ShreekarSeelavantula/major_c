from app.core.adaptive_plan_generator import generate_adaptive_plan
from app.core.retention_scheduler import apply_retention_decay


class PlannerService:

    @staticmethod
    def _make_mongo_safe(data):
        """
        Recursively convert all dictionary keys to strings.
        This prevents MongoDB InvalidDocument errors.
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
    def create_plan(topics, learner_state, hours_per_day, deadline_days):
        """
        High-level planner interface.
        This is what API / frontend will call.
        """

        # Step 1: Apply retention model
        learner_state = apply_retention_decay(learner_state)

        # Step 2: Generate plan
        plan = generate_adaptive_plan(
            topics,
            learner_state,
            hours_per_day,
            deadline_days
        )

        # Step 3: Make Mongo-safe
        safe_plan = PlannerService._make_mongo_safe(plan)

        return safe_plan
