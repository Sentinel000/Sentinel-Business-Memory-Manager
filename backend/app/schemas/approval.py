"""Approval API contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalState
from app.schemas.task import TaskDetail, TaskSummary, TaskUpdate


class ApprovalSummary(BaseModel):
    """A queue row: the decision plus enough of the task to judge it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    state: ApprovalState
    created_at: datetime
    task: TaskSummary


class ApprovalDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    state: ApprovalState
    decided_by_user_id: uuid.UUID | None
    decided_at: datetime | None
    #: What the founder changed, kept so the trail shows the AI's original proposal
    #: alongside the correction.
    edited_payload: dict | None
    rejection_reason: str | None
    created_at: datetime
    #: Full task, including the verbatim source quote — the founder verifies against
    #: that, not against the AI's paraphrase.
    task: TaskDetail


class ApprovalEditRequest(TaskUpdate):
    """Changes to apply. The task stays pending — approving is a separate act."""


class ApprovalRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2_000)


class BulkApproveRequest(BaseModel):
    approval_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class BulkApproveResponse(BaseModel):
    approved: list[uuid.UUID]
    #: Ids that could not be approved, with why — an unknown id, or one already
    #: decided. Reported rather than failing the whole batch.
    skipped: list[dict[str, str]]


class ApprovalListResponse(BaseModel):
    items: list[ApprovalSummary]
    total: int
