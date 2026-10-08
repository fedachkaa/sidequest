import logging
from datetime import datetime
from sqlite3 import Error as SQLiteError
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.ollama_client import OllamaClient
from app.api.errors import service_unavailable
from app.dependencies import get_repository
from app.models.progress import QuestCompletionResponse
from app.models.quest import QuestRequest, StoredQuest
from app.persistence.sqlite_repository import SQLiteRepository
from app.services.progress_service import ProgressService, QuestNotFoundError, QuestNotPendingError
from app.services.quest_service import QuestGenerationError, QuestService


router = APIRouter(prefix="/api/quests", tags=["quests"])
logger = logging.getLogger(__name__)


def get_quest_service() -> QuestService:
    return QuestService(OllamaClient())


@router.post("/generate", response_model=StoredQuest)
def generate_quest(
    request: QuestRequest,
    quest_service: Annotated[QuestService, Depends(get_quest_service)],
    repository: Annotated[SQLiteRepository, Depends(get_repository)],
) -> StoredQuest:
    try:
        quest = quest_service.generate_quest(request)
        return repository.save_generated_quest(
            quest_id=str(uuid4()),
            request=request,
            quest=quest,
            created_at=datetime.now().astimezone(),
        )
    except QuestGenerationError as error:
        logger.exception("Quest generation failed")
        raise service_unavailable(
            "QUEST_ENGINE_UNAVAILABLE",
            "The local quest engine is unavailable right now.",
        ) from error
    except SQLiteError as error:
        logger.exception("Failed to persist generated quest")
        raise service_unavailable(
            "PERSISTENCE_UNAVAILABLE",
            "The field record is unavailable right now.",
        ) from error


@router.get("/{quest_id}", response_model=StoredQuest)
def get_quest_status(
    quest_id: str,
    repository: Annotated[SQLiteRepository, Depends(get_repository)],
) -> StoredQuest:
    try:
        quest = repository.get_quest(quest_id)
    except SQLiteError as error:
        logger.exception("Failed to retrieve quest status")
        raise service_unavailable(
            "PERSISTENCE_UNAVAILABLE",
            "The quest status is unavailable right now.",
        ) from error

    if quest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found.")
    return quest


@router.delete("/{quest_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_quest(
    quest_id: str,
    repository: Annotated[SQLiteRepository, Depends(get_repository)],
) -> None:
    try:
        ProgressService(repository).discard_quest(quest_id)
    except QuestNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found.") from error
    except QuestNotPendingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quest is not available for discard.",
        ) from error
    except SQLiteError as error:
        logger.exception("Failed to discard quest")
        raise service_unavailable(
            "PERSISTENCE_UNAVAILABLE",
            "The quest could not be discarded right now.",
        ) from error


@router.post("/{quest_id}/complete", response_model=QuestCompletionResponse)
def complete_quest(
    quest_id: str,
    repository: Annotated[SQLiteRepository, Depends(get_repository)],
) -> QuestCompletionResponse:
    try:
        return ProgressService(repository).complete_quest(quest_id)
    except QuestNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found.") from error
    except QuestNotPendingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quest is not available for completion.",
        ) from error
    except SQLiteError as error:
        logger.exception("Failed to complete quest")
        raise service_unavailable(
            "PERSISTENCE_UNAVAILABLE",
            "The completion could not be saved right now.",
        ) from error
