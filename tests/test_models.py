from pydantic import ValidationError
import pytest

from app.models.quest import Quest, QuestRequest, Environment, Mode


def test_valid_quest_request() -> None:
    side_quest = QuestRequest(
        duration_minutes=30,
        environment=Environment.NATURE,
        mode=Mode.CALM
    )

    assert side_quest.duration_minutes == 30
    assert side_quest.environment == Environment.NATURE
    assert side_quest.mode == Mode.CALM

def test_invalid_quest_request_duration() -> None:
   with pytest.raises(ValidationError):
    QuestRequest(
        duration_minutes=20,
        environment=Environment.NATURE,
        mode=Mode.CALM
    )

def test_valid_quest() -> None:
    quest = Quest(
        title="Urban Detective",
        duration_minutes=30,
        difficulty=2,
        category="exploration",
        tasks=[
            "Find a building detail you have never noticed before.",
            "Walk down one street you do not normally take.",
            "Stop somewhere and identify five different sounds.",
        ],
    )

    assert quest.title == "Urban Detective"
    assert quest.duration_minutes == 30
    assert quest.difficulty == 2
    assert quest.category == "exploration"
    assert len(quest.tasks) == 3


def test_invalid_quest() -> None:
    with pytest.raises(ValidationError):
        Quest(
            title="Impossible Quest",
            duration_minutes=30,
            difficulty=5,
            category="exploration",
            tasks=[
                "Task one.",
                "Task two.",
            ],
        )