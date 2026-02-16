from app.core.adaptive_plan_generator import generate_adaptive_plan
from app.core.retention_scheduler import apply_retention_decay


class PlannerService:

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

        return plan
