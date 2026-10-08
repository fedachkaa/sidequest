from sqlite3 import Error as SQLiteError

from fastapi import HTTPException, status

from app.persistence.sqlite_repository import SQLiteRepository, database_path_from_environment


def get_repository() -> SQLiteRepository:
    try:
        return SQLiteRepository(database_path_from_environment())
    except (OSError, SQLiteError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local persistence is unavailable. Please try again.",
        ) from error
