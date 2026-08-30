"""Personal material HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from ...auth import current_user_id
from ...core.config import get_settings
from . import repository
from .contracts import (
    PersonalMaterialBlockCreateRequest,
    PersonalMaterialBlockDTO,
    PersonalMaterialBlockListResponse,
    PersonalMaterialBlockUpdateRequest,
    PersonalMaterialRevisionRequest,
)


# The server returns all blocks, including body text, and leaves search/filtering to frontend
# memory. Personal libraries are expected to hold tens to hundreds of blocks; 200 blocks at an
# average 2 KB each is about a 400 KB payload, which is acceptable for this local application.
router = APIRouter(prefix="/api/personal-material")


@router.get("/blocks", response_model=PersonalMaterialBlockListResponse)
def list_blocks(
    include_archived: bool = False,
    user_id: str = Depends(current_user_id),
) -> dict:
    return {
        "items": repository.list_blocks(
            get_settings().db_path,
            user_id,
            include_archived=include_archived,
        ),
    }


@router.post("/blocks", response_model=PersonalMaterialBlockDTO, status_code=201)
def create_block(
    request: PersonalMaterialBlockCreateRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    try:
        return repository.create_block(
            get_settings().db_path,
            user_id,
            request.model_dump(),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/blocks/{block_id}", response_model=PersonalMaterialBlockDTO)
def update_block(
    block_id: int,
    request: PersonalMaterialBlockUpdateRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    fields = request.model_dump()
    expected_revision = fields.pop("expected_revision")
    try:
        result = repository.update_block(
            get_settings().db_path,
            user_id,
            block_id,
            fields,
            expected_revision,
        )
    except repository.PersonalMaterialConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if result is None:
        raise HTTPException(status_code=404, detail="素材块不存在")
    return result


def _set_archived(
    block_id: int,
    request: PersonalMaterialRevisionRequest,
    user_id: str,
    *,
    archived: bool,
) -> dict:
    try:
        result = repository.set_archived(
            get_settings().db_path,
            user_id,
            block_id,
            archived,
            request.expected_revision,
        )
    except repository.PersonalMaterialConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    if result is None:
        raise HTTPException(status_code=404, detail="素材块不存在")
    return result


@router.post("/blocks/{block_id}/archive", response_model=PersonalMaterialBlockDTO)
def archive_block(
    block_id: int,
    request: PersonalMaterialRevisionRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    return _set_archived(block_id, request, user_id, archived=True)


@router.post("/blocks/{block_id}/restore", response_model=PersonalMaterialBlockDTO)
def restore_block(
    block_id: int,
    request: PersonalMaterialRevisionRequest,
    user_id: str = Depends(current_user_id),
) -> dict:
    return _set_archived(block_id, request, user_id, archived=False)
