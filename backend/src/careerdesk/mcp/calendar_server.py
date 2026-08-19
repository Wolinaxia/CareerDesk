"""Local stdio MCP server for the CareerDesk calendar."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from ..core.config import get_settings
from ..features.calendar import repository
from ..features.calendar.contracts import (
    CalendarDate,
    CalendarEventCreateRequest,
    CalendarEventUpdateRequest,
    CalendarTime,
    EventPriority,
    EventType,
    Recurrence,
)
from ..platform.database import DatabaseBusy, init_db


USER_ID_ENV = "CAREERDESK_MCP_USER_ID"
MAX_RANGE_DAYS = 93

mcp = FastMCP(
    "CareerDesk Calendar",
    instructions=(
        "Manage the user's CareerDesk calendar and to-dos. Read an item first and use its "
        "current revision for updates, completion changes, and deletion. Check conflicts before "
        "creating or moving timed items. Deletion additionally requires confirm='DELETE'."
    ),
    log_level="WARNING",
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
IDEMPOTENT_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
DELETE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)


@lru_cache(maxsize=8)
def _initialize(db_path: str) -> None:
    init_db(db_path)
    repository.ensure_schema(db_path)


def _context() -> tuple[str, str]:
    db_path = get_settings().db_path
    _initialize(db_path)
    user_id = os.environ.get(USER_ID_ENV, "me")
    if not user_id or user_id != user_id.strip() or len(user_id) > 256:
        raise ToolError(f"{USER_ID_ENV} must contain 1-256 non-padded characters")
    return db_path, user_id


def _validate_range(start: str, end: str) -> None:
    try:
        first = date.fromisoformat(start)
        last = date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ToolError("start and end must use YYYY-MM-DD") from None
    if first.isoformat() != start or last.isoformat() != end or first > last:
        raise ToolError("calendar date range is invalid")
    if (last - first).days > MAX_RANGE_DAYS:
        raise ToolError("one request may cover at most 94 days")


def _validation_error(error: ValidationError) -> ToolError:
    details = "; ".join(
        ".".join(str(part) for part in item["loc"]) + ": " + item["msg"]
        for item in error.errors(include_url=False)
    )
    return ToolError(f"calendar item is invalid: {details}")


def _repository_error(error: Exception) -> ToolError:
    if isinstance(error, repository.CalendarConflict):
        return ToolError(f"revision conflict: {error}")
    if isinstance(error, repository.CalendarApplicationConflict):
        return ToolError(str(error))
    if isinstance(error, DatabaseBusy):
        return ToolError("CareerDesk is busy; retry the operation")
    return ToolError(str(error))


def _get_owned_event(db_path: str, user_id: str, event_id: int) -> dict:
    item = repository.get_event(db_path, user_id, event_id)
    if item is None:
        raise ToolError("calendar item not found")
    return item


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_calendar_items(start: CalendarDate, end: CalendarDate) -> dict[str, Any]:
    """List events and to-dos in an inclusive date range of at most 94 days."""
    _validate_range(start, end)
    db_path, user_id = _context()
    return {
        "start": start,
        "end": end,
        "items": repository.list_occurrences(db_path, user_id, start, end),
    }


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_calendar_item(event_id: int) -> dict[str, Any]:
    """Get one calendar item by ID, including its current revision."""
    db_path, user_id = _context()
    return _get_owned_event(db_path, user_id, event_id)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_calendar_conflicts(start: CalendarDate, end: CalendarDate) -> dict[str, Any]:
    """List only overlapping timed items, ordered by date and priority."""
    _validate_range(start, end)
    db_path, user_id = _context()
    items = repository.list_occurrences(db_path, user_id, start, end)
    conflicts = [item for item in items if item["conflict_count"] > 1]
    conflicts.sort(key=lambda item: (
        item["occurrence_date"], item["conflict_group"], item["conflict_rank"],
    ))
    return {
        "start": start,
        "end": end,
        "items": conflicts,
    }


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_calendar_applications() -> dict[str, Any]:
    """List job applications that a calendar item may be linked to."""
    db_path, user_id = _context()
    return {"items": repository.list_applications(db_path, user_id)}


@mcp.tool(annotations=WRITE, structured_output=True)
def create_calendar_item(
    title: str,
    date: CalendarDate,
    event_type: EventType = "other",
    priority: EventPriority = "medium",
    start_time: CalendarTime | None = None,
    end_time: CalendarTime | None = None,
    recurrence: Recurrence = "none",
    repeat_until: CalendarDate | None = None,
    location: str | None = None,
    note: str | None = None,
    application_id: int | None = None,
) -> dict[str, Any]:
    """Create an event or timeless to-do. Use event_type='todo' for a to-do."""
    try:
        request = CalendarEventCreateRequest(
            title=title,
            event_type=event_type,
            priority=priority,
            date=date,
            start_time=start_time,
            end_time=end_time,
            recurrence=recurrence,
            repeat_until=repeat_until,
            location=location,
            note=note,
            application_id=application_id,
            completed=False,
        )
    except ValidationError as error:
        raise _validation_error(error) from None
    db_path, user_id = _context()
    try:
        return repository.create_event(db_path, user_id, request.model_dump())
    except (repository.CalendarApplicationConflict, DatabaseBusy, ValueError) as error:
        raise _repository_error(error) from None


@mcp.tool(annotations=IDEMPOTENT_WRITE, structured_output=True)
def update_calendar_item(
    event_id: int,
    expected_revision: int,
    title: str,
    date: CalendarDate,
    event_type: EventType,
    priority: EventPriority,
    start_time: CalendarTime | None = None,
    end_time: CalendarTime | None = None,
    recurrence: Recurrence = "none",
    repeat_until: CalendarDate | None = None,
    location: str | None = None,
    note: str | None = None,
    application_id: int | None = None,
    completed: bool = False,
) -> dict[str, Any]:
    """Replace one item using the current revision returned by a read tool."""
    try:
        request = CalendarEventUpdateRequest(
            title=title,
            event_type=event_type,
            priority=priority,
            date=date,
            start_time=start_time,
            end_time=end_time,
            recurrence=recurrence,
            repeat_until=repeat_until,
            location=location,
            note=note,
            application_id=application_id,
            completed=completed,
            expected_revision=expected_revision,
        )
    except ValidationError as error:
        raise _validation_error(error) from None
    db_path, user_id = _context()
    try:
        result = repository.update_event(db_path, user_id, event_id, request.model_dump())
    except (
        repository.CalendarConflict,
        repository.CalendarApplicationConflict,
        DatabaseBusy,
        ValueError,
    ) as error:
        raise _repository_error(error) from None
    if result is None:
        raise ToolError("calendar item not found")
    return result


@mcp.tool(annotations=IDEMPOTENT_WRITE, structured_output=True)
def set_todo_completed(
    event_id: int, expected_revision: int, completed: bool = True,
) -> dict[str, Any]:
    """Mark a to-do complete or incomplete using its current revision."""
    db_path, user_id = _context()
    existing = _get_owned_event(db_path, user_id, event_id)
    if existing["event_type"] != "todo":
        raise ToolError("only to-do items can be marked complete")
    fields = {
        key: existing[key]
        for key in (
            "title", "event_type", "priority", "date", "start_time", "end_time",
            "recurrence", "repeat_until", "location", "note", "application_id",
        )
    }
    fields["completed"] = completed
    fields["expected_revision"] = expected_revision
    try:
        request = CalendarEventUpdateRequest(**fields)
        result = repository.update_event(db_path, user_id, event_id, request.model_dump())
    except ValidationError as error:
        raise _validation_error(error) from None
    except (repository.CalendarConflict, DatabaseBusy, ValueError) as error:
        raise _repository_error(error) from None
    if result is None:
        raise ToolError("calendar item not found")
    return result


@mcp.tool(annotations=DELETE, structured_output=True)
def delete_calendar_item(
    event_id: int, expected_revision: int, confirm: str,
) -> dict[str, Any]:
    """Permanently delete an item. The confirm value must be exactly 'DELETE'."""
    if confirm != "DELETE":
        raise ToolError("deletion requires confirm='DELETE'")
    db_path, user_id = _context()
    try:
        removed = repository.delete_event(db_path, user_id, event_id, expected_revision)
    except (repository.CalendarConflict, DatabaseBusy) as error:
        raise _repository_error(error) from None
    if not removed:
        raise ToolError("calendar item not found")
    return {"status": "ok", "deleted_id": event_id}


def main() -> None:
    """Run the protocol server without writing non-protocol data to stdout."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
