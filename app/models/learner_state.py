from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LearnerTopicState(BaseModel):
    # Identity
    topic_id: str

    # 🧠 Prior Knowledge (0.0 → 1.0)
    familiarity: float = Field(default=0.0, ge=0.0, le=1.0)

    # ⚡ Learning Speed Multiplier
    # <1.0 = slow, 1.0 = average, >1.0 = fast
    learning_speed: float = Field(default=1.0, ge=0.5, le=2.0)

    # 🧠 Retention Strength (0.0 → 1.0)
    retention_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # 📈 Confidence / Performance Signal
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # 🔁 Interaction Metadata
    attempts: int = 0
    last_studied: Optional[datetime] = None

    # 🔔 Revision Flag
    revision_due: bool = False
