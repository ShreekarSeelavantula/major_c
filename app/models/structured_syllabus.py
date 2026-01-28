from pydantic import BaseModel
from typing import List


class Topic(BaseModel):
    title: str


class Unit(BaseModel):
    unit_number: int
    title: str
    topics: List[Topic]
