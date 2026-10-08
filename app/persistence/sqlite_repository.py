import json
import os
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.models.progress import Progress
from app.models.quest import Quest, QuestRequest, StoredQuest


CompletionStatus = Literal["completed", "unknown", "not_pending"]


class SQLiteRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS quests (
                    id TEXT PRIMARY KEY,
                    duration_minutes INTEGER NOT NULL,
                    environment TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    title TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    tasks_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'superseded')),
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_pending_quest
                    ON quests(status) WHERE status = 'pending';

                CREATE TABLE IF NOT EXISTS progress (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    completed_quests INTEGER NOT NULL DEFAULT 0,
                    outside_minutes INTEGER NOT NULL DEFAULT 0,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    last_completion_date TEXT NOT NULL DEFAULT '',
                    unlocked_badges_json TEXT NOT NULL DEFAULT '[]',
                    environment_counts_json TEXT NOT NULL DEFAULT '{}',
                    mode_counts_json TEXT NOT NULL DEFAULT '{}'
                );

                INSERT OR IGNORE INTO progress (id) VALUES (1);
                """
            )

    def save_generated_quest(
        self,
        quest_id: str,
        request: QuestRequest,
        quest: Quest,
        created_at: datetime,
    ) -> StoredQuest:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE quests SET status = 'superseded' WHERE status = 'pending'")
            connection.execute(
                """
                INSERT INTO quests (
                    id, duration_minutes, environment, mode, title, difficulty,
                    category, tasks_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    quest_id,
                    quest.duration_minutes,
                    request.environment.value,
                    request.mode.value,
                    quest.title,
                    quest.difficulty,
                    quest.category,
                    json.dumps(quest.tasks),
                    created_at.isoformat(),
                ),
            )
        return StoredQuest(
            id=quest_id,
            **quest.model_dump(),
            environment=request.environment,
            mode=request.mode,
            status="pending",
            created_at=created_at,
        )

    def get_pending_quest(self) -> StoredQuest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM quests WHERE status = 'pending' LIMIT 1"
            ).fetchone()
        return self._quest_from_row(row) if row else None

    def get_quest(self, quest_id: str) -> StoredQuest | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)).fetchone()
        return self._quest_from_row(row) if row else None

    def get_progress(self) -> Progress:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM progress WHERE id = 1").fetchone()
        return self._progress_from_row(row)

    def complete_quest(
        self,
        quest_id: str,
        completed_at: datetime,
        update_progress: Callable[[Progress, StoredQuest], Progress],
    ) -> tuple[CompletionStatus, Progress | None]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            quest_row = connection.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)).fetchone()
            if quest_row is None:
                return "unknown", None
            if quest_row["status"] != "pending":
                return "not_pending", None

            quest = self._quest_from_row(quest_row)
            progress_row = connection.execute("SELECT * FROM progress WHERE id = 1").fetchone()
            updated = update_progress(self._progress_from_row(progress_row), quest)
            connection.execute(
                "UPDATE quests SET status = 'completed', completed_at = ? WHERE id = ? AND status = 'pending'",
                (completed_at.isoformat(), quest_id),
            )
            connection.execute(
                """
                UPDATE progress SET
                    total_xp = ?, completed_quests = ?, outside_minutes = ?,
                    current_streak = ?, best_streak = ?, last_completion_date = ?,
                    unlocked_badges_json = ?, environment_counts_json = ?, mode_counts_json = ?
                WHERE id = 1
                """,
                (
                    updated.total_xp,
                    updated.completed_quests,
                    updated.outside_minutes,
                    updated.current_streak,
                    updated.best_streak,
                    updated.last_completion_date,
                    json.dumps(updated.unlocked_badges),
                    json.dumps(updated.environment_counts),
                    json.dumps(updated.mode_counts),
                ),
            )
        return "completed", updated

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _quest_from_row(self, row: sqlite3.Row) -> StoredQuest:
        return StoredQuest(
            id=row["id"],
            duration_minutes=row["duration_minutes"],
            environment=row["environment"],
            mode=row["mode"],
            title=row["title"],
            difficulty=row["difficulty"],
            category=row["category"],
            tasks=json.loads(row["tasks_json"]),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    def _progress_from_row(self, row: sqlite3.Row) -> Progress:
        return Progress(
            total_xp=row["total_xp"],
            completed_quests=row["completed_quests"],
            outside_minutes=row["outside_minutes"],
            current_streak=row["current_streak"],
            best_streak=row["best_streak"],
            last_completion_date=row["last_completion_date"],
            unlocked_badges=json.loads(row["unlocked_badges_json"]),
            environment_counts=json.loads(row["environment_counts_json"]),
            mode_counts=json.loads(row["mode_counts_json"]),
        )


def database_path_from_environment() -> Path:
    return Path(os.environ.get("SIDEQUEST_DB_PATH", "data/sidequest.db"))
