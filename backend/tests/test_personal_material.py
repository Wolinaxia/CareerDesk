"""Personal material validation, concurrency, archiving, and ownership."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from careerdesk.core.config import get_settings
from careerdesk.features.personal_material import repository
from careerdesk.platform.database import now_iso, transaction


@pytest.fixture
def personal_material_client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_LLM_MODEL", "")
    get_settings.cache_clear()
    from careerdesk.bootstrap.app import create_app

    with TestClient(create_app()) as client:
        yield client, get_settings().db_path
    get_settings.cache_clear()


def block(**overrides):
    value = {
        "block_type": "project",
        "language": "zh",
        "title": "智能客服项目",
        "organization": "示例科技",
        "period_start": "2025-03",
        "period_end": None,
        "body": "负责检索增强生成链路，将回答准确率提升至 92%。",
        "tags": ["AI", "Python"],
    }
    value.update(overrides)
    return value


def test_create_and_list_block_returns_tags_and_initial_revision(personal_material_client):
    client, _db_path = personal_material_client
    created = client.post("/api/personal-material/blocks", json=block())
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["tags"] == ["AI", "Python"]
    assert item["revision"] == 1
    assert item["archived"] is False

    response = client.get("/api/personal-material/blocks")
    assert response.status_code == 200, response.text
    assert response.json()["items"] == [item]
    assert "tags_json" not in item


@pytest.mark.parametrize(
    ("block_type", "language", "title", "body"),
    [
        ("invalid", "zh", "标题", "正文"),
        ("project", "fr", "标题", "正文"),
        ("project", "zh", "", "正文"),
        ("project", "zh", "标题", "x" * 8_001),
    ],
)
def test_schema_check_constraints_reject_invalid_rows(
    personal_material_client,
    block_type,
    language,
    title,
    body,
):
    _client, db_path = personal_material_client
    timestamp = now_iso()
    with pytest.raises(sqlite3.IntegrityError), transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO extension_personal_material_blocks ("
            "user_id, block_type, language, title, body, created_time, updated_time) "
            "VALUES ('me', ?, ?, ?, ?, ?, ?)",
            (block_type, language, title, body, timestamp, timestamp),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"period_start": None, "period_end": "2025-06"},
        {"period_start": "2025-07", "period_end": "2025-06"},
        {"period_start": "2025-7", "period_end": None},
        {"period_start": "2025-13", "period_end": None},
    ],
)
def test_period_validation_rejects_incoherent_or_noncanonical_months(
    personal_material_client,
    overrides,
):
    client, _db_path = personal_material_client
    response = client.post("/api/personal-material/blocks", json=block(**overrides))
    assert response.status_code == 422


def test_schema_rejects_end_without_start_and_end_before_start(personal_material_client):
    _client, db_path = personal_material_client
    timestamp = now_iso()
    for period_start, period_end in ((None, "2025-06"), ("2025-07", "2025-06")):
        with pytest.raises(sqlite3.IntegrityError), transaction(db_path) as conn:
            conn.execute(
                "INSERT INTO extension_personal_material_blocks ("
                "user_id, block_type, language, title, period_start, period_end, body, "
                "created_time, updated_time) "
                "VALUES ('me', 'project', 'zh', '标题', ?, ?, '正文', ?, ?)",
                (period_start, period_end, timestamp, timestamp),
            )


def test_tags_are_trimmed_and_deduplicated_case_insensitively(personal_material_client):
    client, _db_path = personal_material_client
    response = client.post(
        "/api/personal-material/blocks",
        json=block(tags=["AI", "ai", " AI ", "", "  ", "Python"]),
    )
    assert response.status_code == 201, response.text
    assert response.json()["tags"] == ["AI", "Python"]


@pytest.mark.parametrize(
    "tags",
    [
        [f"tag-{index}" for index in range(13)],
        ["x" * 25],
    ],
)
def test_tag_limits_are_enforced(personal_material_client, tags):
    client, _db_path = personal_material_client
    response = client.post("/api/personal-material/blocks", json=block(tags=tags))
    assert response.status_code == 422


def test_update_uses_revision_and_api_maps_conflict_to_409(personal_material_client):
    client, db_path = personal_material_client
    item = client.post("/api/personal-material/blocks", json=block()).json()
    updated_payload = block(title="智能客服项目 2.0")
    updated = repository.update_block(
        db_path,
        "me",
        item["id"],
        updated_payload,
        item["revision"],
    )
    assert updated["revision"] == item["revision"] + 1

    with pytest.raises(repository.PersonalMaterialConflict):
        repository.update_block(
            db_path,
            "me",
            item["id"],
            updated_payload,
            item["revision"],
        )
    response = client.put(
        f"/api/personal-material/blocks/{item['id']}",
        json={**updated_payload, "expected_revision": item["revision"]},
    )
    assert response.status_code == 409


def test_archive_hides_block_and_restore_returns_it_to_default_list(personal_material_client):
    client, _db_path = personal_material_client
    item = client.post("/api/personal-material/blocks", json=block()).json()

    archived = client.post(
        f"/api/personal-material/blocks/{item['id']}/archive",
        json={"expected_revision": item["revision"]},
    )
    assert archived.status_code == 200, archived.text
    archived_item = archived.json()
    assert archived_item["archived"] is True
    assert archived_item["revision"] == item["revision"] + 1
    assert client.get("/api/personal-material/blocks").json()["items"] == []
    assert client.get(
        "/api/personal-material/blocks?include_archived=true"
    ).json()["items"] == [archived_item]

    restored = client.post(
        f"/api/personal-material/blocks/{item['id']}/restore",
        json={"expected_revision": archived_item["revision"]},
    )
    assert restored.status_code == 200, restored.text
    restored_item = restored.json()
    assert restored_item["archived"] is False
    assert restored_item["revision"] == archived_item["revision"] + 1
    assert client.get("/api/personal-material/blocks").json()["items"] == [restored_item]


def test_blocks_are_isolated_by_user_id(personal_material_client):
    _client, db_path = personal_material_client
    foreign = repository.create_block(db_path, "user-b", block(title="B 用户素材"))

    assert repository.list_blocks(db_path, "user-a", include_archived=True) == []
    assert repository.update_block(
        db_path,
        "user-a",
        foreign["id"],
        block(title="越权修改"),
        foreign["revision"],
    ) is None
    assert repository.list_blocks(db_path, "user-b", include_archived=True) == [foreign]


def test_archive_and_restore_missing_blocks_return_404(personal_material_client):
    client, _db_path = personal_material_client
    payload = {"expected_revision": 1}

    archived = client.post("/api/personal-material/blocks/999/archive", json=payload)
    restored = client.post("/api/personal-material/blocks/999/restore", json=payload)

    assert archived.status_code == 404
    assert archived.json()["detail"] == "素材块不存在"
    assert restored.status_code == 404
    assert restored.json()["detail"] == "素材块不存在"


def test_set_archived_is_isolated_by_user_id(personal_material_client):
    _client, db_path = personal_material_client
    foreign = repository.create_block(db_path, "user-b", block(title="B 用户素材"))

    assert repository.set_archived(
        db_path,
        "user-a",
        foreign["id"],
        True,
        foreign["revision"],
    ) is None
    assert repository.list_blocks(db_path, "user-b", include_archived=True) == [foreign]


def test_list_blocks_orders_by_updated_time_then_descending_id(personal_material_client):
    client, db_path = personal_material_client
    first = client.post("/api/personal-material/blocks", json=block(title="最早更新")).json()
    second = client.post("/api/personal-material/blocks", json=block(title="同刻较早创建")).json()
    third = client.post("/api/personal-material/blocks", json=block(title="同刻较晚创建")).json()
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE extension_personal_material_blocks SET updated_time = ? WHERE id = ?",
            ("2026-01-01T00:00:00+00:00", first["id"]),
        )
        conn.execute(
            "UPDATE extension_personal_material_blocks SET updated_time = ? WHERE id IN (?, ?)",
            ("2026-02-01T00:00:00+00:00", second["id"], third["id"]),
        )

    items = client.get("/api/personal-material/blocks").json()["items"]
    assert [item["id"] for item in items] == [third["id"], second["id"], first["id"]]


def test_repository_validation_details_reach_client(personal_material_client):
    client, _db_path = personal_material_client

    invalid_month = client.post(
        "/api/personal-material/blocks",
        json=block(period_start="2025-7"),
    )
    oversized_tag = client.post(
        "/api/personal-material/blocks",
        json=block(tags=["x" * 25]),
    )

    assert invalid_month.status_code == 422
    assert invalid_month.json()["detail"] == "月份必须使用 YYYY-MM"
    assert oversized_tag.status_code == 422
    assert oversized_tag.json()["detail"] == "单个标签最多 24 个字符"
