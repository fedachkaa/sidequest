from unittest.mock import Mock
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.ollama_client import OllamaClient
from app.api.quests import get_quest_service
from app.dependencies import get_repository
from app.main import app
from app.models.quest import Quest
from app.persistence.sqlite_repository import SQLiteRepository
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


@pytest.fixture(autouse=True)
def temporary_repository(tmp_path: Path) -> SQLiteRepository:
    repository = SQLiteRepository(tmp_path / "sidequest.db")
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_valid_request_returns_quest_json() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)

    response = client.post("/api/quests/generate", json=valid_request())

    assert response.status_code == 200
    assert response.json()["title"] == quest().title
    assert response.json()["duration_minutes"] == 30
    assert response.json()["environment"] == "city"
    assert response.json()["mode"] == "explore"
    assert response.json()["status"] == "pending"
    assert response.json()["id"]
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
    assert response.json()["title"] == quest().title
    assert response.json()["status"] == "pending"
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


def test_failed_generation_preserves_existing_pending_quest(
    temporary_repository: SQLiteRepository,
) -> None:
    successful_client = Mock(spec=OllamaClient)
    successful_client.generate_quest.return_value = quest()
    use_ollama_stub(successful_client)
    first_response = client.post("/api/quests/generate", json=valid_request())

    failing_client = Mock(spec=OllamaClient)
    failing_client.generate_quest.side_effect = httpx.ConnectError("offline")
    use_ollama_stub(failing_client)
    failed_response = client.post("/api/quests/generate", json=valid_request())

    assert failed_response.status_code == 503
    assert temporary_repository.get_pending_quest().id == first_response.json()["id"]


def test_progress_and_completion_endpoints_persist_updates() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)
    generated = client.post("/api/quests/generate", json=valid_request()).json()

    initial_progress = client.get("/api/progress")
    completion = client.post(f"/api/quests/{generated['id']}/complete")
    repeated_completion = client.post(f"/api/quests/{generated['id']}/complete")
    saved_progress = client.get("/api/progress")

    assert initial_progress.status_code == 200
    assert initial_progress.json()["pending_quest"]["id"] == generated["id"]
    assert completion.status_code == 200
    assert completion.json()["awarded_xp"] == 100
    assert completion.json()["new_badges"] == ["first-steps"]
    assert repeated_completion.status_code == 409
    assert saved_progress.json()["total_xp"] == 100
    assert saved_progress.json()["completed_quests"] == 1
    assert saved_progress.json()["pending_quest"] is None


def test_unknown_quest_completion_returns_404() -> None:
    response = client.post("/api/quests/missing/complete")

    assert response.status_code == 404


def test_new_database_returns_consistent_empty_progress() -> None:
    response = client.get("/api/progress")

    assert response.status_code == 200
    assert response.json() == {
        "total_xp": 0,
        "completed_quests": 0,
        "outside_minutes": 0,
        "current_streak": 0,
        "best_streak": 0,
        "last_completion_date": "",
        "unlocked_badges": [],
        "environment_counts": {},
        "mode_counts": {},
        "pending_quest": None,
    }
