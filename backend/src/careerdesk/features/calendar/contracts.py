"""Strict HTTP contracts for the personal calendar."""

from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


EventType = Literal[
    "course",
    "career_fair",
    "written_test",
    "interview",
    "deadline",
    "todo",
    "other",
]
EventPriority = Literal["high", "medium", "low"]
Recurrence = Literal["none", "weekly"]


def _canonical_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("日期必须使用 YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError("日期必须使用 YYYY-MM-DD")
    return value


def _canonical_time(value: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("时间必须使用 HH:MM") from None
    if parsed.second or parsed.microsecond or parsed.strftime("%H:%M") != value:
        raise ValueError("时间必须使用 HH:MM")
    return value


CalendarDate = Annotated[
    str,
    StringConstraints(min_length=10, max_length=10),
    AfterValidator(_canonical_date),
]
CalendarTime = Annotated[
    str,
    StringConstraints(min_length=5, max_length=5),
    AfterValidator(_canonical_time),
]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2_000)]


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CalendarEventFields(_Contract):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    event_type: EventType
    priority: EventPriority = "medium"
    date: CalendarDate
    start_time: CalendarTime | None = None
    end_time: CalendarTime | None = None
    recurrence: Recurrence = "none"
    repeat_until: CalendarDate | None = None
    location: OptionalText | None = None
    note: OptionalText | None = None
    application_id: int | None = Field(default=None, gt=0)
    completed: bool = False

    @model_validator(mode="after")
    def coherent_schedule(self) -> "CalendarEventFields":
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("开始时间和结束时间必须同时填写")
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("结束时间必须晚于开始时间")
        if self.event_type == "todo":
            if self.start_time is not None:
                raise ValueError("待办事项不能设置具体时间")
            if self.recurrence != "none":
                raise ValueError("待办事项暂不支持重复")
        elif self.completed:
            raise ValueError("只有待办事项可以标记完成")
        if self.recurrence == "none" and self.repeat_until is not None:
            raise ValueError("单次日程不能设置重复截止日期")
        if self.recurrence == "weekly":
            if self.repeat_until is None:
                raise ValueError("每周重复日程需要截止日期")
            start = date.fromisoformat(self.date)
            end = date.fromisoformat(self.repeat_until)
            if end < start:
                raise ValueError("重复截止日期不能早于首次日期")
            if (end - start).days > 730:
                raise ValueError("每周重复最长支持两年")
        return self


class CalendarEventCreateRequest(CalendarEventFields):
    pass


class CalendarEventUpdateRequest(CalendarEventFields):
    expected_revision: int = Field(gt=0)


class CalendarEventDTO(CalendarEventFields):
    id: int = Field(gt=0)
    revision: int = Field(gt=0)
    application_company: str | None = None
    application_position: str | None = None
    created_time: str
    updated_time: str


class CalendarOccurrenceDTO(CalendarEventDTO):
    occurrence_date: CalendarDate
    conflict_group: str | None = None
    conflict_rank: int | None = Field(default=None, ge=0)
    conflict_count: int = Field(default=0, ge=0)


class CalendarEventListResponse(_Contract):
    start: CalendarDate
    end: CalendarDate
    items: list[CalendarOccurrenceDTO]


class CalendarDeleteResponse(_Contract):
    status: Literal["ok"]


class CalendarApplicationDTO(_Contract):
    id: int = Field(gt=0)
    company: str
    position: str


class CalendarApplicationsResponse(_Contract):
    items: list[CalendarApplicationDTO]
