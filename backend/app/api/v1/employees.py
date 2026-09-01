"""Employee routes — the org chart.

Thin: validate, delegate to EmployeeService, return.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import DbSession, EmployeeSvc, FounderUser, TaskSvc
from app.models.employee import Employee
from app.models.enums import TaskStatus
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeLoginCreate,
    EmployeeLoginRead,
    EmployeeLoginUpdate,
    EmployeeSummary,
    EmployeeUpdate,
)
from app.schemas.task import TaskListResponse, TaskSummary

router = APIRouter(prefix="/employees", tags=["employees"])


def _detail(employee: Employee, service) -> EmployeeDetail:
    detail = EmployeeDetail.model_validate(employee)
    detail.manager = (
        EmployeeSummary.model_validate(employee.manager) if employee.manager else None
    )
    detail.reports = [
        EmployeeSummary.model_validate(e) for e in service.reports_of(employee.id)
    ]
    detail.has_login = employee.user is not None
    return detail


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    service: EmployeeSvc,
    _: FounderUser,
    q: Annotated[str | None, Query(max_length=200)] = None,
    unmapped: bool | None = None,
    manager_id: uuid.UUID | None = None,
) -> EmployeeListResponse:
    """List employees.

    A name query returns **every** match. Two people called Mark is exactly the case
    that must stay visibly ambiguous rather than resolve to one of them.
    """
    employees = service.list(search=q, unmapped=unmapped, manager_id=manager_id)
    items = []
    for employee in employees:
        summary = EmployeeSummary.model_validate(employee)
        summary.has_login = employee.user is not None
        items.append(summary)
    return EmployeeListResponse(items=items, total=len(items))


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate, service: EmployeeSvc, _: FounderUser, db: DbSession
) -> EmployeeDetail:
    employee = service.create(payload)
    db.commit()
    db.refresh(employee)
    return _detail(employee, service)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: uuid.UUID, service: EmployeeSvc, _: FounderUser) -> EmployeeDetail:
    """One employee, with their manager and direct reports."""
    return _detail(service.get_or_404(employee_id), service)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    service: EmployeeSvc,
    _: FounderUser,
    db: DbSession,
) -> EmployeeDetail:
    """Edit an employee. Also how the Slack member-list pull writes slack_user_id."""
    employee = service.update(employee_id, payload)
    db.commit()
    db.refresh(employee)
    return _detail(employee, service)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: uuid.UUID, service: EmployeeSvc, _: FounderUser, db: DbSession
) -> None:
    """Delete an employee. 409 while they still own open tasks."""
    service.delete(employee_id)
    db.commit()


@router.get("/{employee_id}/tasks", response_model=TaskListResponse)
def list_employee_tasks(
    employee_id: uuid.UUID,
    service: EmployeeSvc,
    tasks: TaskSvc,
    _: FounderUser,
    status_filter: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    """What is this person working on."""
    employee = service.get_or_404(employee_id)
    filters = {
        "statuses": status_filter,
        "owner_employee_id": employee.id,
        "overdue": None,
        "search": None,
    }
    found = tasks.tasks.list_filtered(**filters, limit=limit, offset=offset)

    items = []
    for task in found:
        summary = TaskSummary.model_validate(task)
        summary.owner_name = employee.name
        items.append(summary)

    return TaskListResponse(
        items=items,
        total=tasks.tasks.count_filtered(**filters),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{employee_id}/login",
    response_model=EmployeeLoginRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee_login(
    employee_id: uuid.UUID,
    payload: EmployeeLoginCreate,
    service: EmployeeSvc,
    _: FounderUser,
    db: DbSession,
) -> EmployeeLoginRead:
    """Provision a login account for an employee."""
    user = service.create_login(employee_id, payload)
    db.commit()
    db.refresh(user)
    return EmployeeLoginRead.model_validate(user)


@router.patch("/{employee_id}/login", response_model=EmployeeLoginRead)
def update_employee_login(
    employee_id: uuid.UUID,
    payload: EmployeeLoginUpdate,
    service: EmployeeSvc,
    _: FounderUser,
    db: DbSession,
) -> EmployeeLoginRead:
    """Update an employee's login credentials or status (e.g. deactivate)."""
    user = service.update_login(employee_id, payload)
    db.commit()
    db.refresh(user)
    return EmployeeLoginRead.model_validate(user)


@router.delete("/{employee_id}/login", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_login(
    employee_id: uuid.UUID,
    service: EmployeeSvc,
    _: FounderUser,
    db: DbSession,
) -> None:
    """Hard-delete an employee's login account, freeing the email address."""
    service.delete_login(employee_id)
    db.commit()
