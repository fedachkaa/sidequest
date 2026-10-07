from app.ai.prompts import build_quest_prompt
from app.models.quest import Environment, Mode, QuestRequest


def test_build_quest_prompt_includes_request_and_constraints() -> None:
    request = QuestRequest(
        duration_minutes=30,
        environment=Environment.PARK,
        mode=Mode.EXPLORE,
    )

    prompt = build_quest_prompt(request)

    assert "30" in prompt
    assert "park" in prompt
    assert "explore" in prompt

    # Receipt must be self-contained
    assert "printed quest receipt" in prompt
    assert "phone" in prompt
    assert "camera" in prompt
    assert "notebook" in prompt
    assert "pen" in prompt
    assert "tools" in prompt
    assert "purchases" in prompt

    # Do not invent the environment
    assert "Never assume" in prompt
    assert "weather condition" in prompt
    assert "predetermined object" in prompt
    assert "whatever is actually present" in prompt

    # Anywhere must really mean anywhere
    assert "built urban environments" in prompt
    assert "natural environments" in prompt

    # Output constraints
    assert "exactly 3 tasks" in prompt
    assert "structured JSON" in prompt