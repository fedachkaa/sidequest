from json import JSONDecodeError

import httpx
from pydantic import ValidationError

from app.ai.ollama_client import OllamaClient
from app.models.quest import Quest, QuestRequest


class QuestDurationMismatchError(Exception):
    def __init__(self, requested_duration: int, generated_duration: int) -> None:
        super().__init__(
            "Generated quest duration does not match the requested duration: "
            f"requested {requested_duration} minutes, generated {generated_duration} minutes."
        )


class QuestGenerationError(Exception):
    pass


class QuestService:
    def __init__(self, ollama_client: OllamaClient) -> None:
        self.ollama_client = ollama_client

    def generate_quest(self, request: QuestRequest) -> Quest:
        for attempt in range(2):
            try:
                return self._generate_quest(request)
            except (
                httpx.HTTPError,
                ValidationError,
                JSONDecodeError,
                KeyError,
                TypeError,
                QuestDurationMismatchError,
            ) as error:
                if attempt == 1:
                    raise QuestGenerationError from error

        raise QuestGenerationError

    def _generate_quest(self, request: QuestRequest) -> Quest:
        quest = self.ollama_client.generate_quest(request)

        if quest.duration_minutes != request.duration_minutes:
            raise QuestDurationMismatchError(
                requested_duration=request.duration_minutes,
                generated_duration=quest.duration_minutes,
            )

        return quest
