import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.quests import router as quests_router
from app.api.progress import router as progress_router
from app.persistence.sqlite_repository import SQLiteRepository, database_path_from_environment


STATIC_DIRECTORY = Path(__file__).parent / "static"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        repository = SQLiteRepository(database_path_from_environment())
        repository.initialize()
    except Exception:
        logger.exception("Failed to initialize the SIDEQUEST SQLite database")
        raise

    application.state.repository = repository
    yield

app = FastAPI(
    title="SIDEQUEST",
    description="AI-generated side quests for the world outside your screen.",
    lifespan=lifespan,
)

app.include_router(quests_router)
app.include_router(progress_router)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


@app.get("/", include_in_schema=False, response_class=FileResponse)
def receipt_machine() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
