"""Public one-tap action links - what the landing page reads and sends."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import TaskStatus

ActionStatus = Literal[TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE]


class ActionPreview(BaseModel):
    """Enough to show the employee what they are about to update, and nothing more.

    Deliberately thin: the link is unauthenticated, so it reveals only the one task
    it was issued for - never other tasks, other people, or the company's data.
    """

    task_id: uuid.UUID
    title: str
    status: TaskStatus
    deadline: datetime | None
    source_quote: str | None
    source_ref: str | None
    owner_name: str
    company_name: str
    #: Done or rejected - the page shows "already closed" instead of the buttons.
    closed: bool


class ActionApply(BaseModel):
    status: ActionStatus
    note: str | None = Field(default=None, max_length=2_000)


class ActionResult(BaseModel):
    task_id: uuid.UUID
    title: str
    status: TaskStatus
    #: False when the task was already in the requested status - a double tap.
    changed: bool
