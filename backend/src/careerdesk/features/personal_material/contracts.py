"""Strict HTTP contracts for reusable personal material blocks."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


BlockType = Literal["project", "work", "education", "skill", "intro", "other"]
MaterialLanguage = Literal["zh", "en"]


MaterialMonth = str
MaterialTags = list[str]


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PersonalMaterialBlockFields(_Contract):
    block_type: BlockType
    language: MaterialLanguage
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    organization: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    ] | None = None
    period_start: MaterialMonth | None = None
    period_end: MaterialMonth | None = None
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8_000)]
    tags: MaterialTags = Field(default_factory=list)


class PersonalMaterialBlockCreateRequest(PersonalMaterialBlockFields):
    pass


class PersonalMaterialBlockUpdateRequest(PersonalMaterialBlockFields):
    expected_revision: int = Field(gt=0)


class PersonalMaterialRevisionRequest(_Contract):
    expected_revision: int = Field(gt=0)


class PersonalMaterialBlockDTO(PersonalMaterialBlockFields):
    id: int = Field(gt=0)
    archived: bool
    revision: int = Field(gt=0)
    created_time: str
    updated_time: str


class PersonalMaterialBlockListResponse(_Contract):
    items: list[PersonalMaterialBlockDTO]
