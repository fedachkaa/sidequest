from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.quests import router as quests_router


STATIC_DIRECTORY = Path(__file__).parent / "static"

app = FastAPI(
    title="SIDEQUEST",
    description="AI-generated side quests for the world outside your screen.",
)

app.include_router(quests_router)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


@app.get("/", include_in_schema=False, response_class=FileResponse)
def receipt_machine() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
