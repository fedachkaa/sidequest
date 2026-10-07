from typing import Protocol

import httpx

from app.ai.prompts import build_quest_prompt
from app.models.quest import Quest, QuestRequest


class HttpClient(Protocol):
    def post(self, url: str, *, json: dict[str, object]) -> httpx.Response: ...


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma3:4b",
        timeout: float = 60.0,
        http_client: HttpClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.http_client = http_client

    def generate_quest(self, request: QuestRequest) -> Quest:
        payload = {
            "model": self.model,
            "prompt": build_quest_prompt(request),
            "format": Quest.model_json_schema(),
            "stream": False,
        }

        if self.http_client is not None:
            return self._send_request(self.http_client, payload)

        with httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
        ) as http_client:
            return self._send_request(http_client, payload)

    def _send_request(
        self,
        http_client: HttpClient,
        payload: dict[str, object],
    ) -> Quest:
        response = http_client.post("/api/generate", json=payload)
        response.raise_for_status()

        ollama_response = response.json()
        return Quest.model_validate_json(ollama_response["response"])
