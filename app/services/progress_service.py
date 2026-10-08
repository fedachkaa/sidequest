from datetime import date, datetime

from app.models.progress import Progress, ProgressResponse, QuestCompletionResponse
from app.models.quest import StoredQuest
from app.persistence.sqlite_repository import CompletionStatus, DiscardStatus, SQLiteRepository


XP_BY_DURATION = {15: 50, 30: 100, 60: 200}
BADGE_IDS = (
    "first-steps",
    "touch-grass",
    "explorer",
    "momentum",
    "outside-regular",
    "one-hour-club",
)


class QuestNotFoundError(Exception):
    pass


class QuestNotPendingError(Exception):
    pass


class ProgressService:
    def __init__(self, repository: SQLiteRepository) -> None:
        self.repository = repository

    def get_progress(self, today: date | None = None) -> ProgressResponse:
        progress = self.repository.get_progress()
        visible_streak = self.visible_streak(progress, today or date.today())
        return ProgressResponse(
            **progress.model_dump(exclude={"current_streak"}),
            current_streak=visible_streak,
            pending_quest=self.repository.get_pending_quest(),
        )

    def complete_quest(
        self,
        quest_id: str,
        completed_at: datetime | None = None,
    ) -> QuestCompletionResponse:
        completion_time = completed_at or datetime.now().astimezone()
        awarded_xp = 0
        new_badges: list[str] = []

        def update(progress: Progress, quest: StoredQuest) -> Progress:
            nonlocal awarded_xp, new_badges
            awarded_xp = XP_BY_DURATION[quest.duration_minutes]
            updated = self._updated_progress(progress, quest, completion_time.date(), awarded_xp)
            new_badges = [badge for badge in updated.unlocked_badges if badge not in progress.unlocked_badges]
            return updated

        completion_status, _ = self.repository.complete_quest(quest_id, completion_time, update)
        self._raise_for_completion_status(completion_status)
        return QuestCompletionResponse(
            progress=self.get_progress(completion_time.date()),
            awarded_xp=awarded_xp,
            new_badges=new_badges,
        )

    def discard_quest(self, quest_id: str) -> None:
        discard_status = self.repository.discard_quest(quest_id)
        self._raise_for_discard_status(discard_status)

    def _updated_progress(
        self,
        progress: Progress,
        quest: StoredQuest,
        completion_date: date,
        awarded_xp: int,
    ) -> Progress:
        completion_date_string = completion_date.isoformat()
        current_streak = self._next_streak(progress, completion_date)
        environment_counts = self._increment(progress.environment_counts, quest.environment.value)
        mode_counts = self._increment(progress.mode_counts, quest.mode.value)
        updated = Progress(
            total_xp=progress.total_xp + awarded_xp,
            completed_quests=progress.completed_quests + 1,
            outside_minutes=progress.outside_minutes + quest.duration_minutes,
            current_streak=current_streak,
            best_streak=max(progress.best_streak, current_streak),
            last_completion_date=completion_date_string,
            unlocked_badges=progress.unlocked_badges,
            environment_counts=environment_counts,
            mode_counts=mode_counts,
        )
        earned = self.earned_badges(updated)
        updated.unlocked_badges = list(dict.fromkeys([*progress.unlocked_badges, *earned]))
        return updated

    def earned_badges(self, progress: Progress) -> list[str]:
        environment_count = sum(count > 0 for count in progress.environment_counts.values())
        conditions = {
            "first-steps": progress.completed_quests >= 1,
            "touch-grass": progress.completed_quests >= 3,
            "explorer": environment_count >= 3,
            "momentum": progress.current_streak >= 3,
            "outside-regular": progress.completed_quests >= 10,
            "one-hour-club": progress.outside_minutes >= 60,
        }
        return [badge for badge in BADGE_IDS if conditions[badge]]

    def visible_streak(self, progress: Progress, today: date) -> int:
        if not progress.last_completion_date:
            return 0
        days_since_completion = (today - date.fromisoformat(progress.last_completion_date)).days
        return progress.current_streak if days_since_completion in (0, 1) else 0

    def _next_streak(self, progress: Progress, completion_date: date) -> int:
        if not progress.last_completion_date:
            return 1
        difference = (completion_date - date.fromisoformat(progress.last_completion_date)).days
        if difference == 0:
            return progress.current_streak
        if difference == 1:
            return progress.current_streak + 1
        return 1

    def _increment(self, counts: dict[str, int], key: str) -> dict[str, int]:
        return {**counts, key: counts.get(key, 0) + 1}

    def _raise_for_completion_status(self, completion_status: CompletionStatus) -> None:
        if completion_status == "unknown":
            raise QuestNotFoundError
        if completion_status == "not_pending":
            raise QuestNotPendingError

    def _raise_for_discard_status(self, discard_status: DiscardStatus) -> None:
        if discard_status == "unknown":
            raise QuestNotFoundError
        if discard_status == "not_pending":
            raise QuestNotPendingError
