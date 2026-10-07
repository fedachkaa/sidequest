from unittest.mock import Mock

import httpx
from fastapi.testclient import TestClient

from app.ai.ollama_client import OllamaClient
from app.api.quests import get_quest_service
from app.main import app
from app.models.quest import Quest
from app.services.quest_service import QuestService


client = TestClient(app)


def quest(duration_minutes: int = 30) -> Quest:
    return Quest(
        title="Urban Detective",
        duration_minutes=duration_minutes,
        difficulty=2,
        category="exploration",
        tasks=["Task one.", "Task two.", "Task three."],
    )


def valid_request() -> dict[str, object]:
    return {
        "duration_minutes": 30,
        "environment": "city",
        "mode": "explore",
    }


def use_ollama_stub(ollama_client: Mock) -> None:
    app.dependency_overrides[get_quest_service] = lambda: QuestService(ollama_client)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_valid_request_returns_quest_json() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 200
    assert response.json() == quest().model_dump(mode="json")
    ollama_client.generate_quest.assert_called_once()


def test_invalid_request_returns_422_without_generation() -> None:
    ollama_client = Mock(spec=OllamaClient)
    use_ollama_stub(ollama_client)

    response = client.post(
        "/api/quests/generate",
        json={"duration_minutes": 20, "environment": "ocean", "mode": "explore"},
    )

    assert response.status_code == 422
    ollama_client.generate_quest.assert_not_called()


def test_first_failure_then_success_returns_quest() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = [httpx.ConnectError("offline"), quest()]
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 200
    assert response.json() == quest().model_dump(mode="json")
    assert ollama_client.generate_quest.call_count == 2


def test_two_failures_return_503() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = httpx.ConnectError("internal details")
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Unable to generate a quest right now. Please try again."
    }
    assert "internal details" not in response.text
    assert ollama_client.generate_quest.call_count == 2


def test_duration_mismatch_then_valid_quest_returns_quest() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = [quest(15), quest(30)]
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 200
    assert response.json()["duration_minutes"] == 30
    assert ollama_client.generate_quest.call_count == 2


def test_two_duration_mismatches_return_503_after_two_attempts() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.side_effect = [quest(15), quest(60), quest(30)]
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 503
    assert ollama_client.generate_quest.call_count == 2
