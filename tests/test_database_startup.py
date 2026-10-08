from datetime import datetime
from pathlib import Path
from sqlite3 import OperationalError

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.models.quest import Environment, Mode, Quest, QuestRequest
from app.persistence.sqlite_repository import (
    DEFAULT_DATABASE_PATH,
    SQLiteRepository,
    PROJECT_ROOT,
    database_path_from_environment,
)


def test_default_database_path_is_stable_when_working_directory_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    assert database_path_from_environment() == DEFAULT_DATABASE_PATH


def test_relative_override_is_resolved_from_project_root(monkeypatch) -> None:
    monkeypatch.setenv("SIDEQUEST_DB_PATH", "custom/storage.db")

    assert database_path_from_environment() == PROJECT_ROOT / "custom/storage.db"


def test_absolute_override_is_preserved(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "absolute.db"
    monkeypatch.setenv("SIDEQUEST_DB_PATH", str(database_path))

    assert database_path_from_environment() == database_path


def test_lifespan_initializes_schema_once_for_multiple_requests(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "nested" / "sidequest.db"
    calls = 0
    original_initialize = SQLiteRepository.initialize

    def count_initialize(repository: SQLiteRepository) -> None:
        nonlocal calls
        calls += 1
        original_initialize(repository)

    monkeypatch.setenv("SIDEQUEST_DB_PATH", str(database_path))
    monkeypatch.setattr(main_module.SQLiteRepository, "initialize", count_initialize)

    with TestClient(app) as client:
        assert client.get("/api/progress").status_code == 200
        assert client.get("/api/progress").status_code == 200

    assert calls == 1
    assert database_path.exists()


def test_persistence_survives_application_restart(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "sidequest.db"
    monkeypatch.setenv("SIDEQUEST_DB_PATH", str(database_path))

    with TestClient(app):
        first_repository = app.state.repository
        first_repository.save_generated_quest(
            "restart-quest",
            QuestRequest(duration_minutes=15, environment=Environment.PARK, mode=Mode.CALM),
            Quest(
                title="Restart Walk",
                duration_minutes=15,
                difficulty=1,
                category="calm",
                tasks=["Task one.", "Task two.", "Task three."],
            ),
            datetime.now(),
        )

    with TestClient(app):
        assert app.state.repository.get_pending_quest().id == "restart-quest"


def test_startup_initialization_failure_is_logged(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_initialize(repository: SQLiteRepository) -> None:
        raise OperationalError("private database details")

    monkeypatch.setattr(main_module.SQLiteRepository, "initialize", fail_initialize)

    with pytest.raises(OperationalError), TestClient(app):
        pass

    assert "Failed to initialize the SIDEQUEST SQLite database" in caplog.text
    assert any(record.exc_info is not None for record in caplog.records)
