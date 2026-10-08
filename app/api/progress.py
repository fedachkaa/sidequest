from typing import Annotated
from sqlite3 import Error as SQLiteError

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_repository
from app.models.progress import ProgressResponse
from app.persistence.sqlite_repository import SQLiteRepository
from app.services.progress_service import ProgressService


router = APIRouter(tags=["progress"])


@router.get("/api/progress", response_model=ProgressResponse)
def get_progress(
    repository: Annotated[SQLiteRepository, Depends(get_repository)],
) -> ProgressResponse:
    try:
        return ProgressService(repository).get_progress()
    except SQLiteError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to load progress right now. Please try again.",
        ) from error
