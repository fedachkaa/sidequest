from pydantic import BaseModel, Field

from app.models.quest import StoredQuest


class Progress(BaseModel):
    total_xp: int = 0
    completed_quests: int = 0
    outside_minutes: int = 0
    current_streak: int = 0
    best_streak: int = 0
    last_completion_date: str = ""
    unlocked_badges: list[str] = Field(default_factory=list)
    environment_counts: dict[str, int] = Field(default_factory=dict)
    mode_counts: dict[str, int] = Field(default_factory=dict)


class ProgressResponse(Progress):
    pending_quest: StoredQuest | None = None


class QuestCompletionResponse(BaseModel):
    progress: ProgressResponse
    awarded_xp: int
    new_badges: list[str]
