"""Task API contracts.

The summary/detail split is rule 4: lists return the minimum, one task returns
everything. The agent tool layer wraps these same shapes in step 5, where a fat
return blows the context even on a short loop.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.enums import ReportedVia, TaskStatus

TERMINAL = (TaskStatus.DONE, TaskStatus.REJECTED)


class TaskCreate(BaseModel):
    """A founder typing a task by hand."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)
    owner_employee_id: uuid.UUID | None = None
    deadline: datetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be blank.")
        return cleaned


class TaskUpdate(BaseModel):
    """Every field optional — only what is sent is changed.

    None is indistinguishable from absent here, so clearing a deadline or unassigning
    an owner needs a dedicated action later rather than PATCH with null.
    """

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)
    owner_employee_id: uuid.UUID | None = None
    deadline: datetime | None = None
    status: TaskStatus | None = None


class StatusUpdateCreate(BaseModel):
    status: TaskStatus
    note: str | None = Field(default=None, max_length=2_000)
    reported_by_employee_id: uuid.UUID | None = None
    reported_via: ReportedVia = ReportedVia.DASHBOARD


class EmployeeStatusUpdateCreate(BaseModel):
    status: Literal[TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE]
    note: str | None = Field(default=None, max_length=2_000)


class StatusUpdateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TaskStatus
    note: str | None
    reported_by_employee_id: uuid.UUID | None
    reported_via: ReportedVia
    created_at: datetime


class _TaskBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: TaskStatus
    deadline: datetime | None
    owner_employee_id: uuid.UUID | None
    owner_name: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_late(self) -> int | None:
        """Days past deadline, or None if not overdue.

        Derived on read for the same reason the filter is: a stored value would go
        stale the moment the clock moved.
        """
        if self.deadline is None or self.status in TERMINAL:
            return None
        delta = datetime.now(UTC) - self.deadline
        return delta.days if delta.days > 0 else None


class TaskSummary(_TaskBase):
    """What a list returns. Deliberately thin — see rule 4."""


class TaskDetail(_TaskBase):
    """One task, in full."""

    description: str | None
    #: Rule 6 — the verbatim citation, so the founder can verify in seconds.
    source_quote: str | None
    source_ref: str | None
    confidence: float | None
    created_by_agent: str | None
    delegated_at: datetime | None
    last_chased_at: datetime | None
    escalated: bool
    created_at: datetime
    updated_at: datetime
    status_updates: list[StatusUpdateRead] = []


class TaskListResponse(BaseModel):
    items: list[TaskSummary]
    total: int
    limit: int
    offset: int


class ReminderRead(BaseModel):
    """A nudge Sentinel sent, shown to the employee it was aimed at.

    Carries the task it is about, because a reminder with no subject is just an
    interruption.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    note: str | None
    deadline: datetime | None
    created_at: datetime
    #: Whether the owner has said anything since this was sent. An answered
    #: reminder stays visible as history but stops counting toward the badge.
    answered: bool = False
