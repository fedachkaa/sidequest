from unittest.mock import Mock
from sqlite3 import OperationalError
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
    repository.initialize()
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
        "detail": {
            "code": "QUEST_ENGINE_UNAVAILABLE",
            "message": "The local quest engine is unavailable right now.",
        }
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


def test_discard_then_generate_replaces_pending_quest() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)
    first = client.post("/api/quests/generate", json=valid_request()).json()

    discarded = client.delete(f"/api/quests/{first['id']}")
    replacement = client.post("/api/quests/generate", json=valid_request()).json()

    assert discarded.status_code == 204
    assert client.get(f"/api/quests/{first['id']}").status_code == 404
    assert client.post(f"/api/quests/{first['id']}/complete").status_code == 404
    assert client.get("/api/progress").json()["pending_quest"]["id"] == replacement["id"]


def test_failed_generation_after_discard_leaves_no_pending_quest() -> None:
    successful_client = Mock(spec=OllamaClient)
    successful_client.generate_quest.return_value = quest()
    use_ollama_stub(successful_client)
    first = client.post("/api/quests/generate", json=valid_request()).json()
    assert client.delete(f"/api/quests/{first['id']}").status_code == 204

    failing_client = Mock(spec=OllamaClient)
    failing_client.generate_quest.side_effect = httpx.ConnectError("offline")
    use_ollama_stub(failing_client)
    failed_generation = client.post("/api/quests/generate", json=valid_request())

    assert failed_generation.status_code == 503
    assert client.get("/api/progress").json()["pending_quest"] is None


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


def test_quest_status_returns_each_persisted_status(
    temporary_repository: SQLiteRepository,
) -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)
    first = client.post("/api/quests/generate", json=valid_request()).json()
    second = client.post("/api/quests/generate", json=valid_request()).json()

    superseded = client.get(f"/api/quests/{first['id']}")
    pending = client.get(f"/api/quests/{second['id']}")
    client.post(f"/api/quests/{second['id']}/complete")
    completed = client.get(f"/api/quests/{second['id']}")

    assert superseded.json()["status"] == "superseded"
    assert pending.json()["status"] == "pending"
    assert completed.json()["status"] == "completed"


def test_unknown_quest_status_returns_404() -> None:
    response = client.get("/api/quests/missing")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "repository_method"),
    [
        ("post", "/api/quests/generate", "save_generated_quest"),
        ("post", "/api/quests/quest-1/complete", "complete_quest"),
        ("delete", "/api/quests/quest-1", "discard_quest"),
        ("get", "/api/progress", "get_progress"),
        ("get", "/api/quests/quest-1", "get_quest"),
    ],
)
def test_persistence_failures_return_stable_error_without_internal_details(
    method: str,
    path: str,
    repository_method: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    repository = Mock(spec=SQLiteRepository)
    getattr(repository, repository_method).side_effect = OperationalError("SQL and path details")
    app.dependency_overrides[get_repository] = lambda: repository
    if path.endswith("generate"):
        ollama_client = Mock(spec=OllamaClient)
        ollama_client.generate_quest.return_value = quest()
        use_ollama_stub(ollama_client)

    response = client.request(
        method.upper(),
        path,
        json=valid_request() if path.endswith("generate") else None,
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PERSISTENCE_UNAVAILABLE"
    assert "SQL and path details" not in response.text
    assert any(record.exc_info is not None for record in caplog.records)


def test_unknown_quest_completion_returns_404() -> None:
    response = client.post("/api/quests/missing/complete")

    assert response.status_code == 404


def test_completed_quest_cannot_be_deleted_and_progress_is_unchanged() -> None:
    ollama_client = Mock(spec=OllamaClient)
    ollama_client.generate_quest.return_value = quest()
    use_ollama_stub(ollama_client)
    generated = client.post("/api/quests/generate", json=valid_request()).json()
    client.post(f"/api/quests/{generated['id']}/complete")
    progress_before_delete = client.get("/api/progress").json()

    response = client.delete(f"/api/quests/{generated['id']}")

    assert response.status_code == 409
    assert client.get(f"/api/quests/{generated['id']}").json()["status"] == "completed"
    assert client.get("/api/progress").json() == progress_before_delete


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
