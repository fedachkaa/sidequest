from app.ai.prompts import build_quest_prompt
from app.models.quest import Environment, Mode, QuestRequest


def test_build_quest_prompt_includes_request_and_constraints() -> None:
    request = QuestRequest(
        duration_minutes=30,
        environment=Environment.PARK,
        mode=Mode.EXPLORE,
    )

    prompt = build_quest_prompt(request)

    assert "Requested duration: 30 minutes" in prompt
    assert "Environment: park" in prompt
    assert "Mode: explore" in prompt
    assert "exactly 3 tasks" in prompt
    assert "difficulty: integer from 1 to 3" in prompt
    assert "Do not require a phone" in prompt
    assert "Do not require purchases" in prompt
    assert "Do not require entering private property" in prompt
    assert "Avoid dangerous activities" in prompt
    assert "specific landmarks, animals, facilities, trails, bodies of water" in prompt
    assert "typical environment of the selected type" in prompt
    assert "Return only structured JSON" in prompt
