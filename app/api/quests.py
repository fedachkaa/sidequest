from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.ollama_client import OllamaClient
from app.models.quest import Quest, QuestRequest
from app.services.quest_service import QuestGenerationError, QuestService


router = APIRouter(prefix="/api/quests", tags=["quests"])


def get_quest_service() -> QuestService:
    return QuestService(OllamaClient())


@router.post("/generate", response_model=Quest)
def generate_quest(
    request: QuestRequest,
    quest_service: Annotated[QuestService, Depends(get_quest_service)],
) -> Quest:
    try:
        return quest_service.generate_quest(request)
    except QuestGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to generate a quest right now. Please try again.",
        ) from error
