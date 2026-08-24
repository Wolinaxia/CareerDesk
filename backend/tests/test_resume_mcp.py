"""End-to-end contract and safety tests for the local resume MCP server."""

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError
import pytest

from careerdesk.core.config import get_settings
from careerdesk.features.resumes import repository as resume_repository
from careerdesk.mcp import resume_server
from careerdesk.platform.database import init_db, now_iso, transaction
from careerdesk.platform.storage.uploads import user_upload_root


@pytest.fixture
def mcp_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("APP_LLM_MODEL", "")
    monkeypatch.setenv("APP_LLM_CONTEXT_WINDOW", "")
    monkeypatch.setenv("APP_LLM_MAX_OUTPUT_TOKENS", "")
    monkeypatch.setenv("APP_RUNTIME_MODE", "test")
    monkeypatch.setenv("APP_DEV_FAKE_USER", "me")
    monkeypatch.setenv("APP_RESUME_MCP_ARCHIVE_SOURCE_ROOTS", str(tmp_path / "resume-sources"))
    get_settings.cache_clear()
    resume_server._initialize.cache_clear()
    db_path = get_settings().db_path
    init_db(db_path)
    yield db_path
    resume_server._initialize.cache_clear()
    get_settings.cache_clear()


def _seed_application(
    db_path: str,
    *,
    user_id: str = "me",
    company: str = "Example Labs",
    position: str = "Backend Engineer",
    jd_text: str = "Build reliable Python services.",
) -> int:
    stamp = now_iso()
    with transaction(db_path) as conn:
        return conn.execute(
            "INSERT INTO applications "
            "(user_id, company, position, jd_text, stage, priority, created_time, updated_time) "
            "VALUES (?, ?, ?, ?, 'backlog', 'high', ?, ?)",
            (user_id, company, position, jd_text, stamp, stamp),
        ).lastrowid


@asynccontextmanager
async def _resume_session():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "careerdesk.mcp.resume_server"],
        env={**os.environ},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            yield session, initialized


def _error_text(result) -> str:
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )


def test_stdio_saves_application_resume_and_reads_it_back(mcp_resume):
    application_id = _seed_application(mcp_resume)

    async def exercise():
        async with _resume_session() as (session, initialized):
            tools = await session.list_tools()
            applications = await session.call_tool("list_applications", {})
            saved = await session.call_tool("save_resume", {
                "name": "Example tailored",
                "content_text": "Python\nFastAPI\nReliable systems",
                "binding": "application",
                "application_id": application_id,
                "family": "backend",
            })
            listed = await session.call_tool("list_resumes", {})
            text = await session.call_tool(
                "get_resume_text", {"resume_id": saved.structuredContent["id"]},
            )
            bound = await session.call_tool(
                "get_application_resume", {"application_id": application_id},
            )
        return initialized, tools, applications, saved, listed, text, bound

    initialized, tools, applications, saved, listed, text, bound = asyncio.run(exercise())
    assert initialized.serverInfo.name == "CareerDesk Resumes"
    tools_by_name = {tool.name: tool for tool in tools.tools}
    assert set(tools_by_name) == {
        "list_applications",
        "get_application_jd",
        "list_resumes",
        "get_resume_text",
        "get_application_resume",
        "save_resume",
        "update_resume_text",
    }
    assert tools_by_name["list_applications"].annotations.readOnlyHint is True
    assert tools_by_name["save_resume"].annotations.idempotentHint is False
    assert tools_by_name["update_resume_text"].annotations.openWorldHint is False
    assert applications.structuredContent["items"][0]["id"] == application_id
    assert saved.isError is False
    assert saved.structuredContent["binding"] == "application"
    assert saved.structuredContent["application_id"] == application_id
    assert saved.structuredContent["annotation_status"] == "pending"
    assert listed.structuredContent["items"] == [{
        "id": saved.structuredContent["id"],
        "name": "Example tailored",
        "binding": "application",
        "application_id": application_id,
        "annotation_status": "pending",
        "archived": False,
        "updated_time": text.structuredContent["updated_time"],
    }]
    assert text.structuredContent["content_text"] == "Python\nFastAPI\nReliable systems"
    assert bound.structuredContent["resume"]["id"] == saved.structuredContent["id"]


def test_stdio_get_application_jd_returns_full_text(mcp_resume):
    jd_text = "Responsibilities:\n" + "Build APIs and data systems.\n" * 200
    application_id = _seed_application(mcp_resume, jd_text=jd_text)

    async def exercise():
        async with _resume_session() as (session, _initialized):
            return await session.call_tool(
                "get_application_jd", {"application_id": application_id},
            )

    result = asyncio.run(exercise())
    assert result.isError is False
    assert result.structuredContent["company"] == "Example Labs"
    assert result.structuredContent["position"] == "Backend Engineer"
    assert result.structuredContent["jd_text"] == jd_text
    assert set(result.structuredContent) == {"id", "company", "position", "jd_text", "jd_parsed"}


def test_stdio_stale_hash_does_not_overwrite_resume(mcp_resume):
    async def exercise():
        async with _resume_session() as (session, _initialized):
            saved = await session.call_tool("save_resume", {
                "name": "Baseline",
                "content_text": "Original text",
                "binding": "family",
            })
            stale = await session.call_tool("update_resume_text", {
                "resume_id": saved.structuredContent["id"],
                "content_text": "Should not win",
                "expected_content_hash": "0" * 64,
            })
            current = await session.call_tool(
                "get_resume_text", {"resume_id": saved.structuredContent["id"]},
            )
        return stale, current

    stale, current = asyncio.run(exercise())
    assert stale.isError is True
    assert "content hash conflict" in _error_text(stale)
    assert current.structuredContent["content_text"] == "Original text"


def test_stdio_rejects_missing_application_binding_and_duplicate_name(mcp_resume):
    async def exercise():
        async with _resume_session() as (session, _initialized):
            missing_application = await session.call_tool("save_resume", {
                "name": "Invalid binding",
                "content_text": "Text",
                "binding": "application",
            })
            first = await session.call_tool("save_resume", {
                "name": "Unique name",
                "content_text": "Keep this text",
                "binding": "family",
            })
            duplicate = await session.call_tool("save_resume", {
                "name": "Unique name",
                "content_text": "Do not overwrite",
                "binding": "family",
            })
            current = await session.call_tool(
                "get_resume_text", {"resume_id": first.structuredContent["id"]},
            )
        return missing_application, duplicate, current

    missing_application, duplicate, current = asyncio.run(exercise())
    assert missing_application.isError is True
    assert "requires application_id" in _error_text(missing_application)
    assert duplicate.isError is True
    assert "already exists" in _error_text(duplicate)
    assert current.structuredContent["content_text"] == "Keep this text"


def test_stdio_identity_comes_only_from_application_local_user(
    mcp_resume, monkeypatch,
):
    application_id = _seed_application(mcp_resume, user_id="me")
    monkeypatch.setenv("CAREERDESK_MCP_USER_ID", "ignored-user")

    async def list_for_current_environment():
        async with _resume_session() as (session, _initialized):
            return await session.call_tool("list_applications", {})

    own = asyncio.run(list_for_current_environment())
    assert [item["id"] for item in own.structuredContent["items"]] == [application_id]

    monkeypatch.setenv("APP_DEV_FAKE_USER", "other-user")
    other = asyncio.run(list_for_current_environment())
    assert other.structuredContent == {"items": []}


def test_stdio_rejects_server_runtime(mcp_resume, monkeypatch):
    monkeypatch.setenv("APP_RUNTIME_MODE", "server")
    monkeypatch.setenv("APP_DEV_FAKE_USER", "")

    async def exercise():
        async with _resume_session() as (session, _initialized):
            return await session.call_tool("list_resumes", {})

    result = asyncio.run(exercise())
    assert result.isError is True
    assert "only in local" in _error_text(result)


def test_stdio_archives_pdf_and_rejects_missing_path(mcp_resume, tmp_path):
    source_root = tmp_path / "resume-sources"
    source_root.mkdir()
    source = source_root / "tailored.pdf"
    source.write_bytes(b"%PDF-1.7\nlocal test archive\n")

    async def exercise():
        async with _resume_session() as (session, _initialized):
            saved = await session.call_tool("save_resume", {
                "name": "Archived source",
                "content_text": "Resume text with archived source",
                "binding": "family",
                "pdf_path": str(source),
            })
            missing = await session.call_tool("save_resume", {
                "name": "Missing source",
                "content_text": "Resume text",
                "binding": "family",
                "pdf_path": str(source_root / "missing.pdf"),
            })
        return saved, missing

    saved, missing = asyncio.run(exercise())
    assert saved.isError is False
    assert "file_path" not in saved.structuredContent
    managed_root = user_upload_root(Path(mcp_resume).parent, "resumes", "me")
    snapshot = resume_repository.get_resume_update_snapshot(
        mcp_resume, "me", saved.structuredContent["id"],
    )
    assert snapshot is not None
    assert snapshot.file_path is not None
    archived = Path(snapshot.file_path)
    assert archived.parent == managed_root
    assert archived.is_file()
    assert archived.read_bytes() == source.read_bytes()
    assert snapshot.file_path == str(archived)
    assert missing.isError is True
    assert "existing local regular file" in _error_text(missing)


def test_archive_source_rejects_final_symlink_and_disallowed_suffix(mcp_resume, tmp_path):
    source_root = tmp_path / "resume-sources"
    source_root.mkdir()
    real_source = source_root / "real.pdf"
    real_source.write_bytes(b"%PDF-1.7\nlocal test archive\n")
    linked_source = source_root / "linked.pdf"
    try:
        linked_source.symlink_to(real_source)
    except (NotImplementedError, OSError):
        pytest.skip("symlinks are unavailable on this filesystem")

    with pytest.raises(ToolError, match="existing local regular file"):
        resume_server._archive_source(str(linked_source))

    executable = source_root / "resume.exe"
    executable.write_bytes(b"not a resume archive")

    with pytest.raises(ToolError, match="pdf_path suffix must be one of"):
        resume_server._archive_source(str(executable))


def test_archive_source_rejects_paths_outside_whitelist(mcp_resume, tmp_path):
    source_root = tmp_path / "resume-sources"
    source_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    outside_source = outside_root / "tailored.pdf"
    outside_source.write_bytes(b"%PDF-1.7\noutside\n")

    with pytest.raises(ToolError, match="allowed local archive source") as caught:
        resume_server._archive_source(str(outside_source))

    assert str(outside_source) not in str(caught.value)

    linked_root = source_root / "linked-outside"
    try:
        linked_root.symlink_to(outside_root, target_is_directory=True)
    except (NotImplementedError, OSError):
        return

    with pytest.raises(ToolError, match="allowed local archive source") as linked:
        resume_server._archive_source(str(linked_root / outside_source.name))

    assert str(linked_root / outside_source.name) not in str(linked.value)


def test_stdio_duplicate_archive_cleanup_removes_rejected_copy(mcp_resume, tmp_path):
    source_root = tmp_path / "resume-sources"
    source_root.mkdir()
    source = source_root / "tailored.pdf"
    source.write_bytes(b"%PDF-1.7\nsingle archived source\n")

    async def exercise():
        async with _resume_session() as (session, _initialized):
            saved = await session.call_tool("save_resume", {
                "name": "Duplicate source",
                "content_text": "Original resume text",
                "binding": "family",
                "pdf_path": str(source),
            })
            duplicate = await session.call_tool("save_resume", {
                "name": "Duplicate source",
                "content_text": "Rejected resume text",
                "binding": "family",
                "pdf_path": str(source),
            })
        return saved, duplicate

    saved, duplicate = asyncio.run(exercise())
    assert saved.isError is False
    assert duplicate.isError is True
    assert "already exists" in _error_text(duplicate)
    managed_root = user_upload_root(Path(mcp_resume).parent, "resumes", "me")
    archived_files = [
        path for path in managed_root.iterdir()
        if not path.is_symlink() and path.is_file()
    ]
    assert len(archived_files) == 1


def test_stdio_list_resumes_marks_archived_rows(mcp_resume):
    async def create_then_list():
        async with _resume_session() as (session, _initialized):
            saved = await session.call_tool("save_resume", {
                "name": "Archived metadata",
                "content_text": "Resume text",
                "binding": "family",
            })
        assert resume_repository.archive_resume(mcp_resume, "me", saved.structuredContent["id"])
        async with _resume_session() as (session, _initialized):
            return await session.call_tool("list_resumes", {"include_archived": True})

    listed = asyncio.run(create_then_list())
    assert listed.isError is False
    assert listed.structuredContent["items"] == [{
        "id": listed.structuredContent["items"][0]["id"],
        "name": "Archived metadata",
        "binding": "family",
        "application_id": None,
        "annotation_status": "pending",
        "archived": True,
        "updated_time": None,
    }]


def test_console_script_handshake_and_tool_contract(mcp_resume):
    """Run the installed console script so a broken entry point cannot ship."""

    async def exercise_protocol():
        executable = Path(sys.executable).with_name(
            "careerdesk-resume-mcp.exe" if os.name == "nt" else "careerdesk-resume-mcp"
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
                result = await session.call_tool("list_resumes", {})
        return initialized, tools, result

    initialized, tools, result = asyncio.run(exercise_protocol())
    assert initialized.serverInfo.name == "CareerDesk Resumes"
    tools_by_name = {tool.name: tool for tool in tools.tools}
    assert set(tools_by_name) == {
        "list_applications",
        "get_application_jd",
        "list_resumes",
        "get_resume_text",
        "get_application_resume",
        "save_resume",
        "update_resume_text",
    }
    assert tools_by_name["get_application_jd"].annotations.readOnlyHint is True
    assert tools_by_name["save_resume"].annotations.destructiveHint is False
    assert tools_by_name["save_resume"].annotations.idempotentHint is False
    assert tools_by_name["update_resume_text"].annotations.openWorldHint is False
    # A loosened Binding literal or an optional hash would silently break clients.
    save_schema = tools_by_name["save_resume"].inputSchema
    assert save_schema["properties"]["binding"]["enum"] == ["family", "application"]
    assert set(save_schema["required"]) == {"name", "content_text", "binding"}
    assert set(tools_by_name["update_resume_text"].inputSchema["required"]) == {
        "resume_id",
        "content_text",
        "expected_content_hash",
    }
    assert result.isError is False
    assert result.structuredContent == {"items": []}
