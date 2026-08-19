"""Calendar HTTP endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from ...auth import current_user_id
from ...core.config import get_settings
from . import repository
from .contracts import (
    CalendarApplicationsResponse,
    CalendarDeleteResponse,
    CalendarEventCreateRequest,
    CalendarEventDTO,
    CalendarEventListResponse,
    CalendarEventUpdateRequest,
)


router = APIRouter(prefix="/api/calendar")


def _range(start: str, end: str) -> tuple[str, str]:
    try:
        first = date.fromisoformat(start)
        last = date.fromisoformat(end)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="日期范围必须使用 YYYY-MM-DD") from None
    if first.isoformat() != start or last.isoformat() != end or first > last:
        raise HTTPException(status_code=422, detail="日历日期范围无效")
    if (last - first).days > 93:
        raise HTTPException(status_code=422, detail="单次最多查询 94 天")
    return start, end


@router.get("/applications", response_model=CalendarApplicationsResponse)
def list_applications(user_id: str = Depends(current_user_id)) -> dict:
    return {
        "items": repository.list_applications(get_settings().db_path, user_id),
    }


@router.get("/events", response_model=CalendarEventListResponse)
def list_events(
    start: str = Query(min_length=10, max_length=10),
    end: str = Query(min_length=10, max_length=10),
    user_id: str = Depends(current_user_id),
) -> dict:
    start, end = _range(start, end)
    return {
        "start": start,
        "end": end,
        "items": repository.list_occurrences(get_settings().db_path, user_id, start, end),
    }


@router.post("/events", response_model=CalendarEventDTO, status_code=201)
def create_event(
    request: CalendarEventCreateRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    try:
        return repository.create_event(
            get_settings().db_path,
            user_id,
            request.model_dump(),
        )
    except repository.CalendarApplicationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/events/{event_id}", response_model=CalendarEventDTO)
def update_event(
    event_id: int,
    request: CalendarEventUpdateRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    try:
        result = repository.update_event(
            get_settings().db_path,
            user_id,
            event_id,
            request.model_dump(),
        )
    except repository.CalendarConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except repository.CalendarApplicationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if result is None:
        raise HTTPException(status_code=404, detail="日程不存在")
    return result


@router.delete("/events/{event_id}", response_model=CalendarDeleteResponse)
def delete_event(
    event_id: int,
    expected_revision: int = Query(gt=0),
    user_id: str = Depends(current_user_id),
) -> dict:
    try:
        removed = repository.delete_event(
            get_settings().db_path,
            user_id,
            event_id,
            expected_revision,
        )
    except repository.CalendarConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    if not removed:
        raise HTTPException(status_code=404, detail="日程不存在")
    return {"status": "ok"}
