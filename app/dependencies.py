from fastapi import Request

from app.persistence.sqlite_repository import SQLiteRepository


def get_repository(request: Request) -> SQLiteRepository:
    return request.app.state.repository
