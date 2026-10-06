from unittest.mock import Mock

import pytest

from app.ai.ollama_client import OllamaClient
from app.models.quest import Environment, Mode, Quest, QuestRequest
from app.services.quest_service import QuestDurationMismatchError, QuestService


def quest_request() -> QuestRequest:
    return QuestRequest(
        duration_minutes=15,
        environment=Environment.PARK,
        mode=Mode.CALM,
    )


def generated_quest(duration_minutes: int) -> Quest:
    return Quest(
        title="Quiet Observer",
        duration_minutes=duration_minutes,
        difficulty=1,
        category="calm",
        tasks=["Task one.", "Task two.", "Task three."],
    )


def test_generate_quest_returns_quest_when_duration_matches() -> None:
    request = quest_request()
    quest = generated_quest(duration_minutes=15)
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest

    result = QuestService(ollama_client).generate_quest(request)

    ollama_client.generate_quest.assert_called_once_with(request)
    assert result is quest


def test_generate_quest_raises_domain_exception_when_duration_mismatches() -> None:
    request = quest_request()
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = generated_quest(duration_minutes=12)

    with pytest.raises(
        QuestDurationMismatchError,
        match="requested 15 minutes, generated 12 minutes",
    ):
        QuestService(ollama_client).generate_quest(request)
