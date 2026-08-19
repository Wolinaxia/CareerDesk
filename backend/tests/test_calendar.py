"""Calendar recurrence, conflicts, ownership, and HTTP contracts."""

import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from careerdesk.core.config import get_settings
from careerdesk.features.applications.repository.mutations import (
    _delete_application_in_transaction,
)
from careerdesk.features.calendar import repository as calendar_repository
from careerdesk.platform.database import init_db, now_iso, transaction


@pytest.fixture
def calendar_client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_LLM_MODEL", "")
    get_settings.cache_clear()
    from careerdesk.bootstrap.app import create_app

    with TestClient(create_app()) as client:
        yield client, get_settings().db_path
    get_settings.cache_clear()


def event(**overrides):
    value = {
        "title": "数据结构课",
        "event_type": "course",
        "priority": "medium",
        "date": "2026-09-07",
        "start_time": "09:00",
        "end_time": "10:30",
        "recurrence": "none",
        "repeat_until": None,
        "location": "教学楼 A101",
        "note": None,
        "application_id": None,
    }
    value.update(overrides)
    return value


def test_weekly_events_expand_and_overlaps_rank_by_priority(calendar_client):
    client, _db_path = calendar_client
    weekly = client.post("/api/calendar/events", json=event(
        recurrence="weekly",
        repeat_until="2026-09-28",
    ))
    assert weekly.status_code == 201, weekly.text
    interview = client.post("/api/calendar/events", json=event(
        title="终面",
        event_type="interview",
        priority="high",
        date="2026-09-14",
        start_time="09:30",
        end_time="10:15",
        location="科技园",
    ))
    assert interview.status_code == 201, interview.text

    response = client.get("/api/calendar/events?start=2026-09-01&end=2026-09-30")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    course_dates = [item["occurrence_date"] for item in items if item["title"] == "数据结构课"]
    assert course_dates == ["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"]
    conflict = [item for item in items if item["occurrence_date"] == "2026-09-14"]
    assert len(conflict) == 2
    assert {item["conflict_count"] for item in conflict} == {2}
    assert [item["title"] for item in sorted(conflict, key=lambda item: item["conflict_rank"])] == [
        "终面",
        "数据结构课",
    ]


def test_event_binding_update_conflict_and_delete_are_tenant_safe(calendar_client):
    client, db_path = calendar_client
    timestamp = now_iso()
    with transaction(db_path) as conn:
        application_id = conn.execute(
            "INSERT INTO applications (user_id, company, position, created_time, updated_time) "
            "VALUES ('me', '示例公司', '产品经理', ?, ?)",
            (timestamp, timestamp),
        ).lastrowid
        foreign_application_id = conn.execute(
            "INSERT INTO applications (user_id, company, position, created_time, updated_time) "
            "VALUES ('other-user', '其他公司', '其他岗位', ?, ?)",
            (timestamp, timestamp),
        ).lastrowid

    assert client.post(
        "/api/calendar/events",
        json=event(application_id=foreign_application_id),
    ).status_code == 409
    created = client.post(
        "/api/calendar/events",
        json=event(title="一面", event_type="interview", priority="high", application_id=application_id),
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["application_company"] == "示例公司"
    assert item["application_position"] == "产品经理"

    updated_payload = {
        **event(title="一面改期", event_type="interview", priority="high", application_id=application_id),
        "expected_revision": item["revision"],
    }
    updated = client.put(f"/api/calendar/events/{item['id']}", json=updated_payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == item["revision"] + 1
    assert client.put(f"/api/calendar/events/{item['id']}", json=updated_payload).status_code == 409
    assert client.delete(
        f"/api/calendar/events/{item['id']}?expected_revision={updated.json()['revision']}"
    ).status_code == 200
    assert client.get("/api/calendar/events?start=2026-09-01&end=2026-09-30").json()["items"] == []


def test_calendar_rejects_invalid_time_and_unbounded_ranges(calendar_client):
    client, _db_path = calendar_client
    assert client.post(
        "/api/calendar/events",
        json=event(start_time="11:00", end_time="10:00"),
    ).status_code == 422
    assert client.post(
        "/api/calendar/events",
        json=event(recurrence="weekly", repeat_until=None),
    ).status_code == 422
    assert client.get(
        "/api/calendar/events?start=2026-01-01&end=2026-12-31"
    ).status_code == 422


def test_todo_is_timeless_and_can_be_checked_off(calendar_client):
    client, _db_path = calendar_client
    created = client.post("/api/calendar/events", json=event(
        title="注册招聘账号",
        event_type="todo",
        start_time=None,
        end_time=None,
        location=None,
        completed=False,
    ))
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["completed"] is False
    assert item["start_time"] is None

    updated = client.put(f"/api/calendar/events/{item['id']}", json={
        **event(
            title="注册招聘账号",
            event_type="todo",
            start_time=None,
            end_time=None,
            location=None,
            completed=True,
        ),
        "expected_revision": item["revision"],
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["completed"] is True
    assert updated.json()["revision"] == item["revision"] + 1

    items = client.get(
        "/api/calendar/events?start=2026-09-01&end=2026-09-30"
    ).json()["items"]
    assert items[0]["title"] == "注册招聘账号"
    assert items[0]["completed"] is True
    assert items[0]["conflict_count"] == 0


def test_todo_rejects_time_recurrence_and_non_todo_completion(calendar_client):
    client, _db_path = calendar_client
    assert client.post("/api/calendar/events", json=event(
        event_type="todo",
        completed=False,
    )).status_code == 422
    assert client.post("/api/calendar/events", json=event(
        event_type="todo",
        start_time=None,
        end_time=None,
        recurrence="weekly",
        repeat_until="2026-09-28",
        completed=False,
    )).status_code == 422
    assert client.post("/api/calendar/events", json=event(
        completed=True,
    )).status_code == 422


def test_calendar_extension_remains_valid_on_next_database_start(calendar_client):
    _client, db_path = calendar_client
    init_db(db_path)


def test_calendar_schema_rejects_null_weekly_end_and_projection_is_defensive(calendar_client):
    _client, db_path = calendar_client
    timestamp = now_iso()
    with pytest.raises(sqlite3.IntegrityError), transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO extension_calendar_events ("
            "user_id, title, event_type, priority, event_date, start_time, end_time, "
            "recurrence, repeat_until, created_time, updated_time) "
            "VALUES ('me', '异常系列', 'other', 'low', '2026-09-07', NULL, NULL, "
            "'weekly', NULL, ?, ?)",
            (timestamp, timestamp),
        )

    corrupt = event(recurrence="weekly", repeat_until=None)
    assert list(calendar_repository._occurrence_dates(
        corrupt, date(2026, 9, 1), date(2026, 9, 30),
    )) == []


def test_calendar_schema_atomically_upgrades_legacy_weekly_constraint(tmp_path):
    db_path = str(tmp_path / "legacy-calendar.db")
    init_db(db_path)
    legacy_schema = (
        calendar_repository.EXTENSION_SCHEMA
        .replace("'deadline', 'todo',\n                       'other'", "'deadline', 'other'")
        .replace(
            "    completed      INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),\n",
            "",
        )
        .replace(
            "    CHECK (event_type != 'todo' OR (\n"
            "        start_time IS NULL AND recurrence = 'none' AND repeat_until IS NULL\n"
            "    )),\n",
            "",
        )
        .replace("    CHECK (event_type = 'todo' OR completed = 0),\n", "")
        .replace(" AND repeat_until IS NOT NULL", "")
    )
    timestamp = now_iso()
    with transaction(db_path) as conn:
        conn.executescript(legacy_schema)
        conn.execute(
            "INSERT INTO extension_calendar_events ("
            "user_id, title, event_type, priority, event_date, start_time, end_time, "
            "recurrence, repeat_until, created_time, updated_time) "
            "VALUES ('me', '旧系列', 'other', 'low', '2026-09-07', NULL, NULL, "
            "'weekly', NULL, ?, ?)",
            (timestamp, timestamp),
        )

    calendar_repository.ensure_schema(db_path)

    with transaction(db_path) as conn:
        sql = conn.execute(
            "SELECT sql FROM sqlite_schema WHERE type='table' "
            "AND name='extension_calendar_events'"
        ).fetchone()[0]
        row = conn.execute(
            "SELECT event_date, repeat_until, completed FROM extension_calendar_events"
        ).fetchone()
    assert "repeat_until IS NOT NULL" in sql
    assert "'todo'" in sql
    assert "completed" in sql
    assert row == ("2026-09-07", "2026-09-07", 0)


def test_calendar_schema_upgrade_preserves_existing_completed_values(tmp_path):
    db_path = str(tmp_path / "intermediate-calendar.db")
    init_db(db_path)
    intermediate_schema = calendar_repository.EXTENSION_SCHEMA.replace(
        " AND repeat_until IS NOT NULL", "",
    )
    timestamp = now_iso()
    with transaction(db_path) as conn:
        conn.executescript(intermediate_schema)
        conn.execute(
            "INSERT INTO extension_calendar_events ("
            "user_id, title, event_type, priority, event_date, start_time, end_time, "
            "recurrence, repeat_until, completed, created_time, updated_time) "
            "VALUES ('me', '已完成旧待办', 'todo', 'medium', '2026-09-07', NULL, NULL, "
            "'none', NULL, 1, ?, ?)",
            (timestamp, timestamp),
        )

    calendar_repository.ensure_schema(db_path)

    with transaction(db_path) as conn:
        row = conn.execute(
            "SELECT event_type, completed FROM extension_calendar_events"
        ).fetchone()
    assert row == ("todo", 1)


def test_application_delete_detaches_calendar_event(calendar_client):
    client, db_path = calendar_client
    timestamp = now_iso()
    with transaction(db_path) as conn:
        application_id = conn.execute(
            "INSERT INTO applications (user_id, company, position, created_time, updated_time) "
            "VALUES ('me', '待删除公司', '工程师', ?, ?)",
            (timestamp, timestamp),
        ).lastrowid
    created = client.post(
        "/api/calendar/events",
        json=event(title="关联面试", application_id=application_id),
    ).json()

    with transaction(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        result = _delete_application_in_transaction(conn, "me", application_id)
    assert result["status"] == "ok"

    item = client.get(
        "/api/calendar/events?start=2026-09-01&end=2026-09-30"
    ).json()["items"][0]
    assert item["id"] == created["id"]
    assert item["application_id"] is None
    assert item["revision"] == created["revision"] + 1
