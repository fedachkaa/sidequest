from fastapi import FastAPI

app = FastAPI(
    title="SIDEQUEST",
    description="AI-generated side quests for the world outside your screen."
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}