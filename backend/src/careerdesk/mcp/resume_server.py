"""Local-only stdio MCP server for CareerDesk resumes.

This module intentionally has no network transport entry point. It trusts the
local desktop data boundary and must never be exposed through SSE or HTTP.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
import stat
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from ..core.config import get_settings
from ..features.applications import public as application_repository
from ..features.resumes import public as resume_repository
from ..platform.database import DatabaseBusy, init_db
from ..platform.storage.uploads import (
    MAX_CHAT_OR_RESUME_BYTES,
    MAX_RESUME_STORAGE_BYTES,
    UploadTooLarge,
    save_upload,
    user_upload_root,
)


LOCAL_RUNTIME_MODES = frozenset({"desktop", "development", "test"})
ARCHIVE_SUFFIXES = frozenset({".pdf", ".docx", ".md", ".txt"})
Binding = Literal["family", "application"]

mcp = FastMCP(
    "CareerDesk Resumes",
    instructions=(
        "Read the target application and its full JD, then read a baseline resume before "
        "creating a tailored version. Resume names are unique and save_resume never overwrites "
        "an existing name. Write calls are not safely retryable: after any error or timeout, "
        "read the resume list and application binding again before retrying. Updates require the "
        "current expected_content_hash returned by get_resume_text. This server is local stdio "
        "only and must never use a network transport."
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


@lru_cache(maxsize=8)
def _initialize(db_path: str) -> None:
    init_db(db_path)


def _context() -> tuple[str, str]:
    settings = get_settings()
    if settings.runtime_mode not in LOCAL_RUNTIME_MODES:
        raise ToolError("resume MCP is available only in local desktop or development mode")
    user_id = settings.dev_fake_user
    if user_id is None:
        raise ToolError("resume MCP requires the application's configured local user")
    db_path = settings.db_path
    _initialize(db_path)
    return db_path, user_id


def _repository_error(error: Exception) -> ToolError:
    if isinstance(error, DatabaseBusy):
        return ToolError("CareerDesk is busy; read current state before retrying")
    if isinstance(error, UploadTooLarge):
        return ToolError("resume archive is too large")
    if isinstance(error, ValueError):
        return ToolError("resume operation failed validation")
    return ToolError("resume operation failed")


def _validate_save_request(
    name: str,
    content_text: str,
    binding: str,
    application_id: int | None,
    family: str | None,
) -> None:
    if not name or len(name) > 200:
        raise ToolError("name must contain between 1 and 200 characters")
    if not content_text:
        raise ToolError("content_text must not be empty")
    if family is not None and len(family) > 100:
        raise ToolError("family must contain at most 100 characters")
    if application_id is not None and application_id <= 0:
        raise ToolError("application_id must be a positive integer")
    if binding not in ("family", "application"):
        raise ToolError("binding must be 'family' or 'application'")
    # Keep this local stdio boundary aligned with features/resumes/api.py:RegisterRequest
    # (originally line 55) without importing the HTTP layer into MCP.
    if binding == "application" and application_id is None:
        raise ToolError("binding='application' requires application_id")
    if binding == "family" and application_id is not None:
        raise ToolError("binding='family' does not accept application_id")


def _archive_source(pdf_path: str) -> Path:
    source = Path(pdf_path).expanduser()
    try:
        info = os.lstat(source)
    except (FileNotFoundError, OSError):
        raise ToolError("pdf_path must point to an existing local regular file") from None
    if not stat.S_ISREG(info.st_mode):
        raise ToolError("pdf_path must point to an existing local regular file")
    if source.suffix.lower() not in ARCHIVE_SUFFIXES:
        allowed = ", ".join(sorted(ARCHIVE_SUFFIXES))
        raise ToolError(f"pdf_path suffix must be one of: {allowed}")
    try:
        resolved_source = source.resolve()
        roots = [root.resolve() for root in get_settings().resume_mcp_archive_source_root_list]
    except (OSError, RuntimeError):
        raise ToolError("pdf_path must point to an existing local regular file") from None
    if not any(resolved_source.is_relative_to(root) for root in roots):
        raise ToolError("pdf_path must be under an allowed local archive source directory")
    return resolved_source


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_applications() -> dict[str, Any]:
    """List the minimum application fields needed to choose a resume target."""
    db_path, user_id = _context()
    board = application_repository.board(db_path, user_id)
    return {
        "items": [
            {
                "id": item["id"],
                "company": item["company"],
                "position": item["position"],
                "stage": item["stage"],
                "priority": item["priority"],
            }
            for column in board["columns"].values()
            for item in column
        ]
    }


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_application_jd(application_id: int) -> dict[str, Any]:
    """Get one application and its complete, untruncated JD text."""
    db_path, user_id = _context()
    item = application_repository.application_detail(db_path, user_id, application_id)
    if item is None:
        raise ToolError("job application not found")
    return {
        "id": item["id"],
        "company": item["company"],
        "position": item["position"],
        "jd_text": item["jd_text"],
        "jd_parsed": item["jd_parsed"],
    }


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_resumes(include_archived: bool = False) -> dict[str, Any]:
    """List resume metadata without copying full resume text into the response."""
    db_path, user_id = _context()
    items = []
    for resume in resume_repository.list_resumes(db_path, user_id, include_archived):
        active_text = resume_repository.get_active_resume_text(
            db_path, user_id, resume["id"],
        )
        items.append({
            "id": resume["id"],
            "name": resume["name"],
            "binding": resume["binding"],
            "application_id": resume["application_id"],
            "annotation_status": resume["annotation_status"],
            "archived": resume["archived"],
            "updated_time": active_text["updated_time"] if active_text is not None else None,
        })
    return {"items": items}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_resume_text(resume_id: int) -> dict[str, Any]:
    """Read active resume text and the hash required for a safe update."""
    db_path, user_id = _context()
    item = resume_repository.get_active_resume_text(db_path, user_id, resume_id)
    if item is None:
        raise ToolError("resume not found or archived")
    return item


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def get_application_resume(application_id: int) -> dict[str, Any]:
    """Get the resume CareerDesk currently selects for an application, if any."""
    db_path, user_id = _context()
    application = application_repository.application_detail(db_path, user_id, application_id)
    if application is None:
        raise ToolError("job application not found")
    return {
        "application_id": application_id,
        "resume": resume_repository.pick_resume_for_application(
            db_path, user_id, application_id,
        ),
    }


@mcp.tool(annotations=WRITE, structured_output=True)
def save_resume(
    name: str,
    content_text: str,
    binding: Binding,
    application_id: int | None = None,
    family: str | None = None,
    pdf_path: str | None = None,
) -> dict[str, Any]:
    """Create a new pending-annotation resume and optionally archive its source file."""
    _validate_save_request(name, content_text, binding, application_id, family)
    db_path, user_id = _context()
    source = _archive_source(pdf_path) if pdf_path is not None else None
    destination: Path | None = None
    keep_destination = False
    try:
        if source is not None:
            root = user_upload_root(Path(db_path).parent, "resumes", user_id)
            with source.open("rb") as stream:
                destination = save_upload(
                    stream,
                    source.name,
                    root,
                    MAX_CHAT_OR_RESUME_BYTES,
                    max_total_bytes=MAX_RESUME_STORAGE_BYTES,
                )
        resume_id = resume_repository.upsert_resume(
            db_path,
            user_id,
            name,
            content_text,
            family=family,
            binding=binding,
            application_id=application_id,
            file_path=str(destination) if destination is not None else None,
            overwrite_existing=False,
        )
        if resume_id is None:
            raise ToolError(
                "a resume with this name already exists; choose another name or use "
                "update_resume_text"
            )
        keep_destination = True
    except ToolError:
        raise
    except (DatabaseBusy, UploadTooLarge, ValueError) as error:
        raise _repository_error(error) from None
    except OSError:
        raise ToolError("resume archive could not be read or stored") from None
    finally:
        if destination is not None and not keep_destination:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass

    saved = resume_repository.get_resume(db_path, user_id, resume_id)
    if saved is None:  # pragma: no cover - the successful transaction owns this row
        raise ToolError("saved resume could not be read back")
    return {
        **saved,
        "annotation_note": "Annotation is pending; trigger resume annotation from CareerDesk UI.",
    }


@mcp.tool(annotations=WRITE, structured_output=True)
def update_resume_text(
    resume_id: int,
    content_text: str,
    expected_content_hash: str,
) -> dict[str, Any]:
    """Replace active resume text only when its current content hash still matches."""
    if (
        len(expected_content_hash) != 64
        or any(character not in "0123456789abcdef" for character in expected_content_hash)
    ):
        raise ToolError("expected_content_hash must be 64 lowercase hexadecimal characters")
    db_path, user_id = _context()
    try:
        status, item = resume_repository.update_active_resume_text(
            db_path,
            user_id,
            resume_id,
            content_text,
            expected_content_hash=expected_content_hash,
        )
    except (DatabaseBusy, ValueError) as error:
        raise _repository_error(error) from None
    if status == "not_found":
        raise ToolError("resume not found or archived")
    if status == "stale":
        raise ToolError("content hash conflict; read the resume again before retrying")
    if item is None:  # pragma: no cover - repository status and payload are paired
        raise ToolError("resume update failed")
    return item


def main() -> None:
    """Run local stdio only, without writing non-protocol data to stdout."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
