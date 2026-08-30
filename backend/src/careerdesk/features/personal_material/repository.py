"""SQLite persistence for reusable personal material blocks."""

from __future__ import annotations

import json
from datetime import date

from ...platform.database import (
    INTERACTIVE_BUSY_TIMEOUT_MS,
    now_iso,
    read_connection,
    transaction,
)


EXTENSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS extension_personal_material_blocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL CHECK (length(user_id) BETWEEN 1 AND 256),
    block_type    TEXT NOT NULL CHECK (block_type IN (
                      'project', 'work', 'education', 'skill', 'intro', 'other')),
    language      TEXT NOT NULL CHECK (language IN ('zh', 'en')),
    title         TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    organization  TEXT CHECK (organization IS NULL OR length(organization) BETWEEN 1 AND 120),
    period_start  TEXT CHECK (period_start IS NULL OR length(period_start) = 7),
    period_end    TEXT CHECK (period_end IS NULL OR length(period_end) = 7),
    body          TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 8000),
    tags_json     TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(tags_json)),
    archived      INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
    revision      INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_time  TEXT NOT NULL,
    updated_time  TEXT NOT NULL,
    CHECK (period_end IS NULL OR period_start IS NOT NULL),
    CHECK (period_end IS NULL OR period_end >= period_start)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_extension_personal_material_user
    ON extension_personal_material_blocks (user_id, archived, updated_time);
"""

_SELECT = (
    "SELECT id, block_type, language, title, organization, period_start, period_end, "
    "body, tags_json, archived, revision, created_time, updated_time "
    "FROM extension_personal_material_blocks "
)


class PersonalMaterialConflict(RuntimeError):
    """The material block changed since the editor loaded it."""


def ensure_schema(db_path: str) -> None:
    """Create the manifest-compatible extension table for existing installations."""
    with read_connection(db_path) as conn:
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{EXTENSION_SCHEMA}")
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise


def _canonical_month(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except (TypeError, ValueError):
        raise ValueError("月份必须使用 YYYY-MM") from None
    if parsed.strftime("%Y-%m") != value:
        raise ValueError("月份必须使用 YYYY-MM")
    return value


def _normalize_tags(values: list[str]) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("标签必须是字符串数组")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("标签必须是字符串数组")
        tag = value.strip()
        if not tag:
            continue
        if len(tag) > 24:
            raise ValueError("单个标签最多 24 个字符")
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(tag)
    if len(normalized) > 12:
        raise ValueError("每个素材块最多 12 个标签")
    return normalized


def _normalized_fields(payload: dict) -> dict:
    period_start = _canonical_month(payload["period_start"])
    period_end = _canonical_month(payload["period_end"])
    # A start without an end intentionally means ongoing and displays as "present".
    if period_end is not None and period_start is None:
        raise ValueError("填写结束月份前必须先填写开始月份")
    if period_end is not None and period_end < period_start:
        raise ValueError("结束月份不能早于开始月份")
    return {
        **payload,
        "period_start": period_start,
        "period_end": period_end,
        "tags_json": json.dumps(
            _normalize_tags(payload["tags"]),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }


def _row(row) -> dict:
    return {
        "id": row[0],
        "block_type": row[1],
        "language": row[2],
        "title": row[3],
        "organization": row[4],
        "period_start": row[5],
        "period_end": row[6],
        "body": row[7],
        "tags": json.loads(row[8]),
        "archived": bool(row[9]),
        "revision": row[10],
        "created_time": row[11],
        "updated_time": row[12],
    }


def list_blocks(db_path: str, user_id: str, *, include_archived: bool) -> list[dict]:
    with read_connection(db_path) as conn:
        condition = "" if include_archived else "AND archived = 0 "
        rows = conn.execute(
            _SELECT + f"WHERE user_id = ? {condition}ORDER BY updated_time DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [_row(row) for row in rows]


def create_block(db_path: str, user_id: str, payload: dict) -> dict:
    fields = _normalized_fields(payload)
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        timestamp = now_iso()
        cursor = conn.execute(
            "INSERT INTO extension_personal_material_blocks ("
            "user_id, block_type, language, title, organization, period_start, period_end, "
            "body, tags_json, created_time, updated_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                fields["block_type"],
                fields["language"],
                fields["title"],
                fields["organization"],
                fields["period_start"],
                fields["period_end"],
                fields["body"],
                fields["tags_json"],
                timestamp,
                timestamp,
            ),
        )
        row = conn.execute(
            _SELECT + "WHERE user_id = ? AND id = ?",
            (user_id, cursor.lastrowid),
        ).fetchone()
        return _row(row)


def update_block(
    db_path: str,
    user_id: str,
    block_id: int,
    payload: dict,
    expected_revision: int,
) -> dict | None:
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT revision FROM extension_personal_material_blocks "
            "WHERE user_id = ? AND id = ?",
            (user_id, block_id),
        ).fetchone()
        if existing is None:
            return None
        if existing[0] != expected_revision:
            raise PersonalMaterialConflict("素材块已在其他窗口修改，请刷新后重试")
        fields = _normalized_fields(payload)
        changed = conn.execute(
            "UPDATE extension_personal_material_blocks SET block_type = ?, language = ?, "
            "title = ?, organization = ?, period_start = ?, period_end = ?, body = ?, "
            "tags_json = ?, revision = revision + 1, updated_time = ? "
            "WHERE user_id = ? AND id = ? AND revision = ?",
            (
                fields["block_type"],
                fields["language"],
                fields["title"],
                fields["organization"],
                fields["period_start"],
                fields["period_end"],
                fields["body"],
                fields["tags_json"],
                now_iso(),
                user_id,
                block_id,
                expected_revision,
            ),
        ).rowcount
        if changed != 1:  # pragma: no cover - protected by BEGIN IMMEDIATE
            raise PersonalMaterialConflict("素材块已在其他窗口修改，请刷新后重试")
        row = conn.execute(
            _SELECT + "WHERE user_id = ? AND id = ?",
            (user_id, block_id),
        ).fetchone()
        return _row(row)


def set_archived(
    db_path: str,
    user_id: str,
    block_id: int,
    archived: bool,
    expected_revision: int,
) -> dict | None:
    with transaction(db_path, busy_timeout_ms=INTERACTIVE_BUSY_TIMEOUT_MS) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT revision FROM extension_personal_material_blocks "
            "WHERE user_id = ? AND id = ?",
            (user_id, block_id),
        ).fetchone()
        if existing is None:
            return None
        if existing[0] != expected_revision:
            raise PersonalMaterialConflict("素材块已在其他窗口修改，请刷新后重试")
        changed = conn.execute(
            "UPDATE extension_personal_material_blocks SET archived = ?, "
            "revision = revision + 1, updated_time = ? "
            "WHERE user_id = ? AND id = ? AND revision = ?",
            (archived, now_iso(), user_id, block_id, expected_revision),
        ).rowcount
        if changed != 1:  # pragma: no cover - protected by BEGIN IMMEDIATE
            raise PersonalMaterialConflict("素材块已在其他窗口修改，请刷新后重试")
        row = conn.execute(
            _SELECT + "WHERE user_id = ? AND id = ?",
            (user_id, block_id),
        ).fetchone()
        return _row(row)
