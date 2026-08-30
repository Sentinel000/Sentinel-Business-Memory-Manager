"""Employee task routes — the employee-facing surface."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import CurrentEmployeeId, DbSession, EmployeeUser, TaskSvc
from app.models.enums import ReportedVia, TaskStatus
from app.schemas.task import (
    EmployeeStatusUpdateCreate,
    StatusUpdateCreate,
    TaskDetail,
    TaskListResponse,
    TaskSummary,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/tasks", response_model=TaskListResponse)
def list_my_tasks(
    employee_id: CurrentEmployeeId,
    tasks: TaskSvc,
    _: EmployeeUser,
    status_filter: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    """List tasks assigned to the authenticated employee."""
    filters = {
        "statuses": status_filter,
        "owner_employee_id": employee_id,
        "overdue": None,
        "search": None,
    }
    found = tasks.tasks.list_filtered(**filters, limit=limit, offset=offset)

    items = [TaskSummary.model_validate(task) for task in found]
    return TaskListResponse(
        items=items,
        total=tasks.tasks.count_filtered(**filters),
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_my_task(
    task_id: uuid.UUID,
    employee_id: CurrentEmployeeId,
    tasks: TaskSvc,
    _: EmployeeUser,
) -> TaskDetail:
    """Detail view for a task owned by the authenticated employee."""
    task = tasks.get_owned_or_404(task_id, employee_id)
    return TaskDetail.model_validate(task)


@router.post("/tasks/{task_id}/status", response_model=TaskDetail)
def update_my_task_status(
    task_id: uuid.UUID,
    payload: EmployeeStatusUpdateCreate,
    employee_id: CurrentEmployeeId,
    tasks: TaskSvc,
    _: EmployeeUser,
    db: DbSession,
) -> TaskDetail:
    """Report status (IN_PROGRESS, BLOCKED, DONE) on an owned task."""
    task = tasks.get_owned_or_404(task_id, employee_id)

    full_payload = StatusUpdateCreate(
        status=payload.status,
        note=payload.note,
        reported_by_employee_id=employee_id,
        reported_via=ReportedVia.DASHBOARD,
    )
    updated_task = tasks.record_status(task.id, full_payload)
    db.commit()
    db.refresh(updated_task)
    return TaskDetail.model_validate(updated_task)
