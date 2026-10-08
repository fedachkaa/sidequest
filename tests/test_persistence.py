from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.models.progress import Progress
from app.models.quest import Environment, Mode, Quest, QuestRequest
from app.persistence.sqlite_repository import SQLiteRepository
from app.services.progress_service import ProgressService, QuestNotPendingError


def initialized_repository(database_path: Path) -> SQLiteRepository:
    repository = SQLiteRepository(database_path)
    repository.initialize()
    return repository


def request(
    duration_minutes: int = 30,
    environment: Environment = Environment.CITY,
    mode: Mode = Mode.EXPLORE,
) -> QuestRequest:
    return QuestRequest(
        duration_minutes=duration_minutes,
        environment=environment,
        mode=mode,
    )


def quest(duration_minutes: int = 30) -> Quest:
    return Quest(
        title="Field Test",
        duration_minutes=duration_minutes,
        difficulty=1,
        category="exploration",
        tasks=["Task one.", "Task two.", "Task three."],
    )


def save_quest(
    repository: SQLiteRepository,
    quest_request: QuestRequest | None = None,
) -> str:
    selected_request = quest_request or request()
    quest_id = str(uuid4())
    repository.save_generated_quest(
        quest_id,
        selected_request,
        quest(selected_request.duration_minutes),
        datetime(2026, 10, 1, 12),
    )
    return quest_id


def test_database_initializes_and_persists_after_reopening(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "sidequest.db"
    repository = initialized_repository(database_path)
    quest_id = save_quest(repository)

    reopened = initialized_repository(database_path)

    assert database_path.exists()
    assert reopened.get_pending_quest().id == quest_id
    assert reopened.get_progress() == Progress()


def test_new_quest_supersedes_previous_pending_quest(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    first_id = save_quest(repository)
    second_id = save_quest(repository, request(environment=Environment.PARK))

    assert repository.get_quest(first_id).status == "superseded"
    assert repository.get_pending_quest().id == second_id

    with pytest.raises(QuestNotPendingError):
        ProgressService(repository).complete_quest(first_id)


@pytest.mark.parametrize(
    ("duration_minutes", "expected_xp"),
    [(15, 50), (30, 100), (60, 200)],
)
def test_completion_awards_expected_xp_once(
    tmp_path: Path,
    duration_minutes: int,
    expected_xp: int,
) -> None:
    repository = initialized_repository(tmp_path / f"{duration_minutes}.db")
    quest_id = save_quest(repository, request(duration_minutes=duration_minutes))
    service = ProgressService(repository)

    result = service.complete_quest(quest_id, datetime(2026, 10, 7, 12))

    assert result.awarded_xp == expected_xp
    assert result.progress.total_xp == expected_xp
    with pytest.raises(QuestNotPendingError):
        service.complete_quest(quest_id, datetime(2026, 10, 7, 13))
    assert repository.get_progress().total_xp == expected_xp


def test_streak_handles_same_consecutive_and_missed_days(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    service = ProgressService(repository)

    first_id = save_quest(repository)
    service.complete_quest(first_id, datetime(2026, 1, 31, 9))
    same_day_id = save_quest(repository)
    same_day = service.complete_quest(same_day_id, datetime(2026, 1, 31, 18))
    next_day_id = save_quest(repository)
    next_day = service.complete_quest(next_day_id, datetime(2026, 2, 1, 9))
    missed_day_id = save_quest(repository)
    after_gap = service.complete_quest(missed_day_id, datetime(2026, 2, 3, 9))

    assert same_day.progress.current_streak == 1
    assert next_day.progress.current_streak == 2
    assert after_gap.progress.current_streak == 1
    assert after_gap.progress.best_streak == 2
    assert service.get_progress(date(2026, 2, 5)).current_streak == 0


def test_streak_handles_year_boundary(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    service = ProgressService(repository)

    first_id = save_quest(repository)
    service.complete_quest(first_id, datetime(2026, 12, 31, 12))
    second_id = save_quest(repository)
    result = service.complete_quest(second_id, datetime(2027, 1, 1, 12))

    assert result.progress.current_streak == 2


def test_streak_increments_across_device_local_midnight(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    service = ProgressService(repository)
    device_timezone = timezone(timedelta(hours=2))

    first_id = save_quest(repository)
    service.complete_quest(
        first_id,
        datetime(2026, 10, 7, 23, 59, tzinfo=device_timezone),
    )
    second_id = save_quest(repository)
    result = service.complete_quest(
        second_id,
        datetime(2026, 10, 8, 0, 1, tzinfo=device_timezone),
    )

    assert result.progress.current_streak == 2


def test_all_badges_unlock_and_remain_persisted(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    service = ProgressService(repository)
    environments = [Environment.CITY, Environment.PARK, Environment.NATURE]

    for index in range(10):
        quest_id = save_quest(
            repository,
            request(duration_minutes=15, environment=environments[index % 3]),
        )
        completion_day = min(index + 1, 3)
        service.complete_quest(quest_id, datetime(2026, 10, completion_day, 12))

    progress = initialized_repository(repository.database_path).get_progress()

    assert progress.completed_quests == 10
    assert progress.outside_minutes == 150
    assert set(progress.unlocked_badges) == {
        "first-steps",
        "touch-grass",
        "explorer",
        "momentum",
        "outside-regular",
        "one-hour-club",
    }


def test_concurrent_completion_awards_only_once(tmp_path: Path) -> None:
    repository = initialized_repository(tmp_path / "sidequest.db")
    quest_id = save_quest(repository)

    def complete() -> str:
        try:
            ProgressService(repository).complete_quest(quest_id, datetime(2026, 10, 7, 12))
            return "completed"
        except QuestNotPendingError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: complete(), range(2)))

    assert sorted(outcomes) == ["completed", "rejected"]
    assert repository.get_progress().total_xp == 100
