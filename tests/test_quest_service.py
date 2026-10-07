from unittest.mock import Mock

import httpx
import pytest

from app.ai.ollama_client import OllamaClient
from app.models.quest import Environment, Mode, Quest, QuestRequest
from app.services.quest_service import QuestGenerationError, QuestService


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


def test_generate_quest_retries_when_duration_mismatches() -> None:
    request = quest_request()
    ollama_client = Mock(spec=OllamaClient)
    valid_quest = generated_quest(duration_minutes=15)
    ollama_client.generate_quest.side_effect = [
        generated_quest(duration_minutes=12),
        valid_quest,
    ]

    result = QuestService(ollama_client).generate_quest(request)

    assert result is valid_quest
    assert ollama_client.generate_quest.call_count == 2


def test_generate_quest_raises_generation_error_after_two_failures() -> None:
    request = quest_request()
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = httpx.ConnectError("Ollama unavailable")

    with pytest.raises(QuestGenerationError):
        QuestService(ollama_client).generate_quest(request)

    assert ollama_client.generate_quest.call_count == 2


def test_generate_quest_does_not_retry_unexpected_errors() -> None:
    request = quest_request()
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = RuntimeError("unexpected error")

    with pytest.raises(RuntimeError, match="unexpected error"):
        QuestService(ollama_client).generate_quest(request)

    ollama_client.generate_quest.assert_called_once_with(request)
