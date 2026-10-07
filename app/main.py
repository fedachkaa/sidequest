from fastapi import FastAPI

from app.api.quests import router as quests_router


app = FastAPI(
    title="SIDEQUEST",
    description="AI-generated side quests for the world outside your screen.",
)

app.include_router(quests_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
