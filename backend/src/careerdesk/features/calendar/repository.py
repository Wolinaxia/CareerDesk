"""SQLite persistence and occurrence projection for calendar events."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from ...platform.database import (
    INTERACTIVE_BUSY_TIMEOUT_MS,
    now_iso,
    read_connection,
    transaction,
)


EXTENSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS extension_calendar_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL CHECK (length(user_id) BETWEEN 1 AND 256),
    title          TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    event_type     TEXT NOT NULL CHECK (event_type IN (
                       'course', 'career_fair', 'written_test', 'interview', 'deadline', 'todo',
                       'other'
                   )),
    priority       TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    event_date     TEXT NOT NULL CHECK (length(event_date) = 10),
    start_time     TEXT CHECK (start_time IS NULL OR length(start_time) = 5),
    end_time       TEXT CHECK (end_time IS NULL OR length(end_time) = 5),
    recurrence     TEXT NOT NULL CHECK (recurrence IN ('none', 'weekly')),
    repeat_until   TEXT CHECK (repeat_until IS NULL OR length(repeat_until) = 10),
    location       TEXT CHECK (location IS NULL OR length(location) <= 2000),
    note           TEXT CHECK (note IS NULL OR length(note) <= 2000),
    application_id INTEGER,
    completed      INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    revision       INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_time   TEXT NOT NULL,
    updated_time   TEXT NOT NULL,
    CHECK ((start_time IS NULL) = (end_time IS NULL)),
    CHECK (start_time IS NULL OR end_time > start_time),
    CHECK (event_type != 'todo' OR (
        start_time IS NULL AND recurrence = 'none' AND repeat_until IS NULL
    )),
    CHECK (event_type = 'todo' OR completed = 0),
    CHECK (
        (recurrence = 'none' AND repeat_until IS NULL)
        OR (recurrence = 'weekly' AND repeat_until IS NOT NULL AND repeat_until >= event_date)
    )
) STRICT;
CREATE INDEX IF NOT EXISTS idx_extension_calendar_user_date
    ON extension_calendar_events (user_id, event_date, repeat_until);
"""

_SELECT = (
    "SELECT event.id, event.title, event.event_type, event.priority, event.event_date, "
    "event.start_time, event.end_time, event.recurrence, event.repeat_until, "
    "event.location, event.note, event.application_id, event.completed, event.revision, "
    "application.company, application.position, event.created_time, event.updated_time "
    "FROM extension_calendar_events AS event "
    "LEFT JOIN applications AS application ON application.id = event.application_id "
    "AND application.user_id = event.user_id "
)


class CalendarConflict(RuntimeError):
    """The event changed since the editor loaded it."""


class CalendarApplicationConflict(RuntimeError):
    """The application selected by the editor no longer exists."""


def ensure_schema(db_path: str) -> None:
    """Create the manifest-compatible extension table for existing installations."""
    with read_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT sql FROM sqlite_schema WHERE type = 'table' "
            "AND name = 'extension_calendar_events'"
        ).fetchone()
        existing_sql = (existing[0] or "") if existing is not None else ""
        needs_constraint_upgrade = existing is not None and (
            "repeat_until IS NOT NULL" not in existing_sql
            or "completed" not in existing_sql
            or "'todo'" not in existing_sql
        )
        migration = ""
        if needs_constraint_upgrade:
            migration = """
ALTER TABLE extension_calendar_events RENAME TO extension_calendar_events_legacy;
DROP INDEX IF EXISTS idx_extension_calendar_user_date;
"""
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{migration}\n{EXTENSION_SCHEMA}")
            if needs_constraint_upgrade:
                conn.execute(
                    "INSERT INTO extension_calendar_events ("
                    "id, user_id, title, event_type, priority, event_date, start_time, "
                    "end_time, recurrence, repeat_until, location, note, application_id, "
                    "completed, revision, created_time, updated_time) "
                    "SELECT id, user_id, title, event_type, priority, event_date, start_time, "
                    "end_time, recurrence, CASE WHEN recurrence = 'weekly' "
                    "AND repeat_until IS NULL THEN event_date ELSE repeat_until END, "
                    "location, note, application_id, "
                    f"{'completed' if 'completed' in existing_sql else '0'}, "
                    "revision, created_time, updated_time "
                    "FROM extension_calendar_events_legacy"
                )
                conn.execute("DROP TABLE extension_calendar_events_legacy")
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise


def _application_exists(conn, user_id: str, application_id: int | None) -> bool:
    if application_id is None:
        return True
    return conn.execute(
        "SELECT 1 FROM applications WHERE user_id = ? AND id = ?",
        (user_id, application_id),
    ).fetchone() is not None


def _row(row) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "event_type": row[2],
        "priority": row[3],
        "date": row[4],
        "start_time": row[5],
        "end_time": row[6],
        "recurrence": row[7],
        "repeat_until": row[8],
        "location": row[9],
        "note": row[10],
        "application_id": row[11],
        "completed": bool(row[12]),
        "revision": row[13],
        "application_company": row[14],
        "application_position": row[15],
        "created_time": row[16],
        "updated_time": row[17],
    }


def create_event(db_path: str, user_id: str, fields: dict) -> dict:
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not _application_exists(conn, user_id, fields["application_id"]):
            raise CalendarApplicationConflict("关联岗位不存在或已被删除")
        timestamp = now_iso()
        cursor = conn.execute(
            "INSERT INTO extension_calendar_events ("
            "user_id, title, event_type, priority, event_date, start_time, end_time, "
            "recurrence, repeat_until, location, note, application_id, completed, "
            "created_time, updated_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                fields["title"],
                fields["event_type"],
                fields["priority"],
                fields["date"],
                fields["start_time"],
                fields["end_time"],
                fields["recurrence"],
                fields["repeat_until"],
                fields["location"] or None,
                fields["note"] or None,
                fields["application_id"],
                fields["completed"],
                timestamp,
                timestamp,
            ),
        )
        row = conn.execute(
            _SELECT + "WHERE event.user_id = ? AND event.id = ?",
            (user_id, cursor.lastrowid),
        ).fetchone()
        return _row(row)


def update_event(db_path: str, user_id: str, event_id: int, fields: dict) -> dict | None:
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT revision FROM extension_calendar_events WHERE user_id = ? AND id = ?",
            (user_id, event_id),
        ).fetchone()
        if existing is None:
            return None
        if existing[0] != fields["expected_revision"]:
            raise CalendarConflict("日程已在其他窗口修改，请刷新后重试")
        if not _application_exists(conn, user_id, fields["application_id"]):
            raise CalendarApplicationConflict("关联岗位不存在或已被删除")
        changed = conn.execute(
            "UPDATE extension_calendar_events SET title = ?, event_type = ?, priority = ?, "
            "event_date = ?, start_time = ?, end_time = ?, recurrence = ?, repeat_until = ?, "
            "location = ?, note = ?, application_id = ?, completed = ?, "
            "revision = revision + 1, updated_time = ? "
            "WHERE user_id = ? AND id = ? AND revision = ?",
            (
                fields["title"], fields["event_type"], fields["priority"], fields["date"],
                fields["start_time"], fields["end_time"], fields["recurrence"],
                fields["repeat_until"], fields["location"] or None, fields["note"] or None,
                fields["application_id"], fields["completed"], now_iso(), user_id, event_id,
                fields["expected_revision"],
            ),
        ).rowcount
        if changed != 1:  # pragma: no cover - protected by BEGIN IMMEDIATE
            raise CalendarConflict("日程已在其他窗口修改，请刷新后重试")
        row = conn.execute(
            _SELECT + "WHERE event.user_id = ? AND event.id = ?",
            (user_id, event_id),
        ).fetchone()
        return _row(row)


def delete_event(
    db_path: str,
    user_id: str,
    event_id: int,
    expected_revision: int,
) -> bool:
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT revision FROM extension_calendar_events WHERE user_id = ? AND id = ?",
            (user_id, event_id),
        ).fetchone()
        if existing is None:
            return False
        if existing[0] != expected_revision:
            raise CalendarConflict("日程已在其他窗口修改，请刷新后重试")
        return conn.execute(
            "DELETE FROM extension_calendar_events WHERE user_id = ? AND id = ? AND revision = ?",
            (user_id, event_id, expected_revision),
        ).rowcount == 1


def get_event(db_path: str, user_id: str, event_id: int) -> dict | None:
    """Return one owned calendar item without expanding recurrence."""
    with read_connection(db_path) as conn:
        row = conn.execute(
            _SELECT + "WHERE event.user_id = ? AND event.id = ?",
            (user_id, event_id),
        ).fetchone()
    return None if row is None else _row(row)


def _occurrence_dates(event: dict, range_start: date, range_end: date):
    first = date.fromisoformat(event["date"])
    if event["recurrence"] == "none":
        if range_start <= first <= range_end:
            yield first
        return
    repeat_until = event.get("repeat_until")
    if repeat_until is None:
        return
    final = date.fromisoformat(repeat_until)
    current = first
    if current < range_start:
        current += timedelta(days=((range_start - current).days + 6) // 7 * 7)
    while current <= range_end and current <= final:
        yield current
        current += timedelta(days=7)


def _minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _add_conflicts(items: list[dict]) -> None:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        if item["start_time"] is not None:
            by_date[item["occurrence_date"]].append(item)
    priority = {"high": 0, "medium": 1, "low": 2}
    for occurrence_date, candidates in by_date.items():
        remaining = set(range(len(candidates)))
        while remaining:
            component = {remaining.pop()}
            changed = True
            while changed:
                changed = False
                for index in list(remaining):
                    candidate = candidates[index]
                    if any(
                        _minutes(candidate["start_time"]) < _minutes(candidates[member]["end_time"])
                        and _minutes(candidates[member]["start_time"]) < _minutes(candidate["end_time"])
                        for member in component
                    ):
                        component.add(index)
                        remaining.remove(index)
                        changed = True
            if len(component) < 2:
                continue
            ordered = sorted(
                (candidates[index] for index in component),
                key=lambda item: (
                    priority[item["priority"]], item["start_time"], item["end_time"], item["id"],
                ),
            )
            group = f"{occurrence_date}:" + "-".join(str(item["id"]) for item in ordered)
            for rank, item in enumerate(ordered):
                item["conflict_group"] = group
                item["conflict_rank"] = rank
                item["conflict_count"] = len(ordered)


def list_occurrences(db_path: str, user_id: str, start: str, end: str) -> list[dict]:
    range_start = date.fromisoformat(start)
    range_end = date.fromisoformat(end)
    with read_connection(db_path) as conn:
        rows = conn.execute(
            _SELECT
            + "WHERE event.user_id = ? AND event.event_date <= ? "
            "AND (event.recurrence = 'none' OR event.repeat_until >= ?) "
            "ORDER BY event.event_date, event.start_time, event.id",
            (user_id, end, start),
        ).fetchall()
    items: list[dict] = []
    for raw in rows:
        event = _row(raw)
        for occurrence_date in _occurrence_dates(event, range_start, range_end):
            items.append({
                **event,
                "occurrence_date": occurrence_date.isoformat(),
                "conflict_group": None,
                "conflict_rank": None,
                "conflict_count": 0,
            })
    _add_conflicts(items)
    priority = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda item: (
        item["occurrence_date"], item["start_time"] is None, item["start_time"] or "24:00",
        item["event_type"] == "todo", item["completed"], priority[item["priority"]], item["id"],
    ))
    return items


def list_applications(db_path: str, user_id: str) -> list[dict]:
    with read_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, company, position FROM applications WHERE user_id = ? "
            "ORDER BY updated_time DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [{"id": row[0], "company": row[1], "position": row[2]} for row in rows]
