from app.models.quest import QuestRequest


def build_quest_prompt(request: QuestRequest) -> str:
    return f"""Generate one outdoor SIDEQUEST as structured JSON.

Requested duration: {request.duration_minutes} minutes
Environment: {request.environment.value}
Mode: {request.mode.value}

Return only a JSON object with these fields:
- title: string
- duration_minutes: integer, exactly {request.duration_minutes}
- difficulty: integer from 1 to 3
- category: string
- tasks: array of exactly 3 strings

Rules:
- Respect the requested duration, environment, and mode.
- Generate exactly 3 tasks that fit within the total requested duration.
- Do not require a phone or other screen.
- Do not require purchases.
- Do not require entering private property.
- Avoid dangerous activities.
- Do not assume that specific landmarks, animals, facilities, trails, bodies of water,
  or other environmental features exist.
- Make every task achievable in a typical environment of the selected type.
- Return only structured JSON, with no Markdown fences or explanatory text.
"""
