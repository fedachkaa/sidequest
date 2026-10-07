import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.ollama_client import OllamaClient
from app.models.quest import Environment, Mode, QuestRequest


class StubHttpClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.path = ""
        self.payload: dict[str, object] = {}

    def post(self, path: str, *, json: dict[str, object]) -> httpx.Response:
        self.path = path
        self.payload = json
        return self.response

    def __enter__(self) -> "StubHttpClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def quest_request() -> QuestRequest:
    return QuestRequest(
        duration_minutes=30,
        environment=Environment.CITY,
        mode=Mode.EXPLORE,
    )


def test_generate_quest_calls_ollama_and_returns_validated_quest() -> None:
    request = httpx.Request("POST", "http://ollama.test/api/generate")
    response = httpx.Response(
        200,
        request=request,
        json={
            "response": json.dumps(
                {
                    "title": "Urban Detective",
                    "duration_minutes": 30,
                    "difficulty": 2,
                    "category": "exploration",
                    "tasks": ["Task one.", "Task two.", "Task three."],
                }
            )
        },
    )
    http_client = StubHttpClient(response)

    quest = OllamaClient(http_client=http_client).generate_quest(quest_request())

    quest_schema = http_client.payload["format"]

    assert http_client.path == "/api/generate"
    assert http_client.payload["model"] == "gemma3:4b"
    assert http_client.payload["stream"] is False
    assert isinstance(quest_schema, dict)
    assert quest_schema["properties"]["tasks"]["minItems"] == 3

    assert quest.title == "Urban Detective"
    assert quest.duration_minutes == 30
    assert quest.difficulty == 2
    assert len(quest.tasks) == 3


@pytest.mark.parametrize("timeout", [60.0, 120.0])
def test_generate_quest_configures_real_http_client(
    monkeypatch: pytest.MonkeyPatch,
    timeout: float,
) -> None:
    request = httpx.Request("POST", "http://ollama.test/api/generate")
    response = httpx.Response(
        200,
        request=request,
        json={
            "response": json.dumps(
                {
                    "title": "Urban Detective",
                    "duration_minutes": 30,
                    "difficulty": 2,
                    "category": "exploration",
                    "tasks": ["Task one.", "Task two.", "Task three."],
                }
            )
        },
    )
    http_client = StubHttpClient(response)
    client_arguments: dict[str, object] = {}

    def create_http_client(**kwargs: object) -> StubHttpClient:
        client_arguments.update(kwargs)
        return http_client

    monkeypatch.setattr(httpx, "Client", create_http_client)

    client = OllamaClient() if timeout == 60.0 else OllamaClient(timeout=timeout)
    client.generate_quest(quest_request())

    assert client_arguments == {
        "base_url": "http://localhost:11434",
        "timeout": timeout,
    }


def test_generate_quest_rejects_invalid_quest() -> None:
    request = httpx.Request("POST", "http://ollama.test/api/generate")
    response = httpx.Response(
        200,
        request=request,
        json={
            "response": json.dumps(
                {
                    "title": "Invalid Quest",
                    "duration_minutes": 30,
                    "difficulty": 4,
                    "category": "exploration",
                    "tasks": ["Task one.", "Task two."],
                }
            )
        },
    )
    http_client = StubHttpClient(response)

    with pytest.raises(ValidationError):
        OllamaClient(http_client=http_client).generate_quest(quest_request())


def test_generate_quest_raises_for_ollama_http_error() -> None:
    request = httpx.Request("POST", "http://ollama.test/api/generate")
    response = httpx.Response(500, request=request)
    http_client = StubHttpClient(response)

    with pytest.raises(httpx.HTTPStatusError):
        OllamaClient(http_client=http_client).generate_quest(quest_request())
