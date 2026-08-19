"""Contract and safety tests for the local calendar MCP server."""

import asyncio
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from careerdesk.core.config import get_settings
from careerdesk.mcp import calendar_server


@pytest.fixture
def mcp_calendar(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("APP_LLM_MODEL", "")
    monkeypatch.setenv("APP_RUNTIME_MODE", "test")
    monkeypatch.setenv("APP_DEV_FAKE_USER", "me")
    get_settings.cache_clear()
    calendar_server._initialize.cache_clear()
    yield
    calendar_server._initialize.cache_clear()
    get_settings.cache_clear()


def test_mcp_create_list_conflicts_and_complete_todo(mcp_calendar):
    course = calendar_server.create_calendar_item(
        title="算法课",
        date="2026-09-07",
        event_type="course",
        priority="medium",
        start_time="09:00",
        end_time="10:30",
    )
    interview = calendar_server.create_calendar_item(
        title="一面",
        date="2026-09-07",
        event_type="interview",
        priority="high",
        start_time="09:30",
        end_time="10:00",
    )
    todo = calendar_server.create_calendar_item(
        title="注册招聘账号",
        date="2026-09-07",
        event_type="todo",
    )

    listed = calendar_server.list_calendar_items("2026-09-01", "2026-09-30")
    assert {item["id"] for item in listed["items"]} == {
        course["id"], interview["id"], todo["id"],
    }
    conflicts = calendar_server.list_calendar_conflicts("2026-09-01", "2026-09-30")
    assert [item["title"] for item in conflicts["items"]] == ["一面", "算法课"]
    completed = calendar_server.set_todo_completed(todo["id"], todo["revision"], True)
    assert completed["completed"] is True
    assert completed["revision"] == todo["revision"] + 1


def test_mcp_revision_and_delete_guards(mcp_calendar):
    item = calendar_server.create_calendar_item(
        title="投递截止",
        date="2026-09-12",
        event_type="deadline",
        priority="high",
    )
    updated = calendar_server.update_calendar_item(
        event_id=item["id"],
        expected_revision=item["revision"],
        title="投递截止（更新）",
        date=item["date"],
        event_type=item["event_type"],
        priority=item["priority"],
    )

    with pytest.raises(ToolError, match="revision conflict"):
        calendar_server.update_calendar_item(
            event_id=item["id"],
            expected_revision=item["revision"],
            title="过期修改",
            date=item["date"],
            event_type=item["event_type"],
            priority=item["priority"],
        )
    with pytest.raises(ToolError, match="confirm='DELETE'"):
        calendar_server.delete_calendar_item(item["id"], updated["revision"], "yes")

    assert calendar_server.delete_calendar_item(
        item["id"], updated["revision"], "DELETE",
    ) == {"status": "ok", "deleted_id": item["id"]}


def test_mcp_identity_comes_from_application_local_user(mcp_calendar, monkeypatch):
    monkeypatch.setenv("CAREERDESK_MCP_USER_ID", "ignored-user")
    assert calendar_server._context()[1] == "me"
    item = calendar_server.create_calendar_item(
        title="私人待办",
        date="2026-09-10",
        event_type="todo",
    )
    monkeypatch.setenv("APP_DEV_FAKE_USER", "other-user")
    get_settings.cache_clear()
    assert calendar_server.list_calendar_items("2026-09-01", "2026-09-30")["items"] == []
    with pytest.raises(ToolError, match="not found"):
        calendar_server.get_calendar_item(item["id"])


def test_mcp_rejects_server_runtime(mcp_calendar, monkeypatch):
    monkeypatch.setenv("APP_RUNTIME_MODE", "server")
    monkeypatch.setenv("APP_DEV_FAKE_USER", "")
    get_settings.cache_clear()
    with pytest.raises(ToolError, match="only in local"):
        calendar_server.list_calendar_items("2026-09-01", "2026-09-30")


def test_mcp_rejects_invalid_ranges_and_todo_times(mcp_calendar):
    with pytest.raises(ToolError, match="at most 94 days"):
        calendar_server.list_calendar_items("2026-01-01", "2026-12-31")
    with pytest.raises(ToolError, match=r"item: invalid value \(value_error\)"):
        calendar_server.create_calendar_item(
            title="错误待办",
            date="2026-09-10",
            event_type="todo",
            start_time="09:00",
            end_time="10:00",
        )


def test_mcp_stdio_handshake_and_read_tool(mcp_calendar):
    async def exercise_protocol():
        executable = Path(sys.executable).with_name(
            "careerdesk-calendar-mcp.exe" if os.name == "nt" else "careerdesk-calendar-mcp"
        )
        assert executable.is_file()
        parameters = StdioServerParameters(
            command=str(executable),
            env={
                **os.environ,
                "APP_DATA_DIR": get_settings().data_dir,
                "APP_LLM_MODEL": "",
            },
        )
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("list_calendar_items", {
                    "start": "2026-09-01",
                    "end": "2026-09-30",
                })
        return initialized, tools, result

    initialized, tools, result = asyncio.run(exercise_protocol())
    assert initialized.serverInfo.name == "CareerDesk Calendar"
    tools_by_name = {tool.name: tool for tool in tools.tools}
    assert set(tools_by_name) == {
        "list_calendar_items",
        "get_calendar_item",
        "list_calendar_conflicts",
        "list_calendar_applications",
        "create_calendar_item",
        "update_calendar_item",
        "set_todo_completed",
        "delete_calendar_item",
    }
    assert tools_by_name["list_calendar_items"].annotations.readOnlyHint is True
    assert tools_by_name["create_calendar_item"].annotations.destructiveHint is False
    assert tools_by_name["update_calendar_item"].annotations.idempotentHint is False
    assert tools_by_name["set_todo_completed"].annotations.idempotentHint is False
    assert tools_by_name["delete_calendar_item"].annotations.destructiveHint is True
    assert tools_by_name["delete_calendar_item"].annotations.openWorldHint is False
    create_properties = tools_by_name["create_calendar_item"].inputSchema["properties"]
    assert create_properties["location"]["anyOf"][0]["maxLength"] == 2_000
    assert create_properties["note"]["anyOf"][0]["maxLength"] == 2_000
    assert result.isError is False
    assert result.structuredContent == {
        "start": "2026-09-01",
        "end": "2026-09-30",
        "items": [],
    }
