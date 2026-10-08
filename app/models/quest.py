from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from enum import Enum


class Environment(str, Enum):
    CITY = "city"
    PARK = "park"
    NATURE = "nature"
    ANYWHERE = "anywhere"


class Mode(str, Enum):
    CALM = "calm"
    MOVE = "move"
    EXPLORE = "explore"
    SURPRISE = "surprise"


class QuestRequest(BaseModel):
    duration_minutes: Literal[15, 30, 60]
    environment: Environment
    mode: Mode


class Quest(BaseModel):
    title: str
    duration_minutes: int
    difficulty: int = Field(ge=1, le=3)
    category: str
    tasks: list[str] = Field(min_length=3, max_length=3)


class StoredQuest(Quest):
    id: str
    environment: Environment
    mode: Mode
    status: Literal["pending", "completed", "superseded"]
    created_at: datetime
    completed_at: datetime | None = None
