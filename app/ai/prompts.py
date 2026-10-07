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
- The duration_minutes field MUST be exactly {request.duration_minutes}.
- Generate exactly 3 tasks that fit within the total requested duration.

- The participant must be able to complete the entire quest using only:
  1. the printed quest receipt,
  2. themselves,
  3. things they happen to encounter around them.

- Do not require a phone, camera, notebook, pen, tools, purchases, or any other equipment.
- Do not require entering private property or doing anything dangerous.

- Never assume that a specific object, animal, plant, landmark, facility,
  surface, trail, body of water, or weather condition exists.
- Do not require finding a predetermined object such as a specific leaf,
  stone, flower, button, glove, bird, tree, or bench.
- Instead, phrase tasks adaptively around things the participant can choose
  from whatever is actually present in their surroundings.

- Every task must still be achievable if expected environmental features
  are absent.
- For "anywhere", tasks must work in both built urban environments and
  natural environments.

Mode behavior:
- calm: slow observation, sensory awareness, or quiet reflection.
- move: walking and physical movement should be central to the quest.
- explore: encourage discovery and noticing unfamiliar or overlooked details.
- surprise: create a playful or unexpected activity while remaining practical.

Quest quality:
- Create original tasks rather than repeating generic task templates.
- Make the three tasks meaningfully different from each other.
- Make the quest feel playful and memorable, not like a generic mindfulness exercise.
- The three tasks together should reasonably fill the requested duration.
- For longer quests, prefer activities involving continued movement or exploration
  rather than asking the participant to stare at one object for a long time.

Return only structured JSON, with no Markdown fences or explanatory text.
"""