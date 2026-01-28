from pydantic import BaseModel
from typing import List, Optional


class Topic(BaseModel):
    title: str
    difficulty: Optional[str] = None
    estimated_hours: Optional[int] = None


class Unit(BaseModel):
    name: str
    topics: List[Topic]


class StructuredSyllabus(BaseModel):
    units: List[Unit]
