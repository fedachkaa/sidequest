from typing import Annotated
from datetime import datetime
from sqlite3 import Error as SQLiteError
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.ollama_client import OllamaClient
from app.dependencies import get_repository
from app.models.progress import QuestCompletionResponse
from app.models.quest import QuestRequest, StoredQuest
from app.persistence.sqlite_repository import SQLiteRepository
from app.services.progress_service import ProgressService, QuestNotFoundError, QuestNotPendingError
from app.services.quest_service import QuestGenerationError, QuestService


router = APIRouter(prefix="/api/quests", tags=["quests"])


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
    except (QuestGenerationError, SQLiteError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to generate a quest right now. Please try again.",
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update progress right now. Please try again.",
        ) from error
