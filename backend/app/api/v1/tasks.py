"""Task routes.

Thin by design: validate, delegate to TaskService, return. Business rules live in the
service, tenant scoping in the repository. Errors are raised as domain exceptions —
handlers in app/exceptions.py render the structured shape.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, Response, status

from app.dependencies import DbSession, FounderUser, TaskSvc
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.task import (
    StatusUpdateCreate,
    TaskCreate,
    TaskDetail,
    TaskListResponse,
    TaskSummary,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_summary(task: Task, owner_names: dict[uuid.UUID, str]) -> TaskSummary:
    summary = TaskSummary.model_validate(task)
    summary.owner_name = owner_names.get(task.owner_employee_id) if task.owner_employee_id else None
    return summary


@router.post("", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    service: TaskSvc,
    current_user: FounderUser,
    db: DbSession,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TaskDetail:
    """Create a task by hand.

    Approved at creation with a recorded approval row — the founder is the approval
    step. Send an Idempotency-Key header to make a retried or double-clicked submit
    return the original task instead of a duplicate.
    """
    task, created = service.create_manual(
        payload, created_by=current_user, idempotency_key=idempotency_key
    )
    db.commit()
    db.refresh(task)

    if not created:
        response.status_code = status.HTTP_200_OK

    detail = TaskDetail.model_validate(task)
    detail.owner_name = service.owner_names([task]).get(task.owner_employee_id)
    return detail


@router.get("", response_model=TaskListResponse)
def list_tasks(
    service: TaskSvc,
    _: FounderUser,
    status_filter: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    owner_employee_id: uuid.UUID | None = None,
    overdue: bool | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: Annotated[str, Query(pattern="^(deadline|created_at|title)$")] = "created_at",
    descending: bool = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    """List tasks. Returns summaries only — use the detail route for one task."""
    filters = {
        "statuses": status_filter,
        "owner_employee_id": owner_employee_id,
        "overdue": overdue,
        "search": q,
    }
    tasks = service.tasks.list_filtered(**filters, sort=sort, descending=descending, limit=limit, offset=offset)
    names = service.owner_names(tasks)

    return TaskListResponse(
        items=[_to_summary(t, names) for t in tasks],
        total=service.tasks.count_filtered(**filters),
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: uuid.UUID, service: TaskSvc, _: FounderUser) -> TaskDetail:
    """One task in full, with its status timeline."""
    task = service.get_or_404(task_id)
    detail = TaskDetail.model_validate(task)
    detail.owner_name = service.owner_names([task]).get(task.owner_employee_id)
    return detail


@router.patch("/{task_id}", response_model=TaskDetail)
def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, service: TaskSvc, _: FounderUser, db: DbSession
) -> TaskDetail:
    """Edit a task. Only the fields sent are changed."""
    task = service.update(task_id, payload)
    db.commit()
    db.refresh(task)

    detail = TaskDetail.model_validate(task)
    detail.owner_name = service.owner_names([task]).get(task.owner_employee_id)
    return detail


@router.post("/{task_id}/status", response_model=TaskDetail)
def record_status(
    task_id: uuid.UUID,
    payload: StatusUpdateCreate,
    service: TaskSvc,
    _: FounderUser,
    db: DbSession,
) -> TaskDetail:
    """Append a timeline entry and move the task to that status.

    The dashboard equivalent of an employee tapping a Slack button.
    """
    task = service.record_status(task_id, payload)
    db.commit()
    db.refresh(task)

    detail = TaskDetail.model_validate(task)
    detail.owner_name = service.owner_names([task]).get(task.owner_employee_id)
    return detail


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, service: TaskSvc, _: FounderUser, db: DbSession) -> None:
    """Remove a task. Cascades to its timeline and approval row."""
    service.delete(task_id)
    db.commit()
