"""Employee business logic — the org chart.

Two rules worth naming, because both protect the follow-up agent:

* a manager chain may not loop, or escalation would recurse forever
* an employee who owns open tasks cannot be deleted out from under them
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.employee import Employee
from app.models.enums import TaskStatus, UserRole
from app.models.user import User
from app.repositories.task import TERMINAL_STATUSES, TaskRepository
from app.repositories.user import UserRepository, find_user_for_login
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeLoginCreate,
    EmployeeLoginUpdate,
    EmployeeUpdate,
)
from app.services.base import TenantService

#: Statuses that still need someone to act. The inverse of TERMINAL_STATUSES, minus
#: rejected tasks, which nobody owes anything on.
OPEN_STATUSES = tuple(s for s in TaskStatus if s not in TERMINAL_STATUSES)


class EmployeeService(TenantService):
    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        super().__init__(db, company_id)
        self.tasks = TaskRepository(db, company_id)
        self.users = UserRepository(db, company_id)

    def get_or_404(self, employee_id: uuid.UUID) -> Employee:
        employee = self.employees.get(employee_id)
        if employee is None:
            raise NotFoundError("Employee not found.")
        return employee

    # --- manager chain ----------------------------------------------------------

    def _check_manager(self, employee_id: uuid.UUID | None, manager_id: uuid.UUID | None) -> None:
        """Reject a manager who is foreign, themselves, or downstream of them.

        A cycle here would make escalation recurse forever, so it is caught on write
        rather than defended against on every read.
        """
        if manager_id is None:
            return

        self.require_own_employee(manager_id, field="manager")

        if employee_id is not None and manager_id == employee_id:
            raise ValidationError("An employee cannot manage themselves.")

        if employee_id is None:
            return

        # Walk up from the proposed manager. Meeting this employee means the edge
        # would close a loop. The guard counts iterations too, in case existing data
        # already contains one.
        seen: set[uuid.UUID] = set()
        current = self.employees.get(manager_id)
        while current is not None and current.manager_id is not None:
            if current.manager_id == employee_id:
                raise ValidationError(
                    "That would create a management cycle — the proposed manager "
                    "already reports to this employee."
                )
            if current.manager_id in seen:
                break
            seen.add(current.manager_id)
            current = self.employees.get(current.manager_id)

    # --- commands ---------------------------------------------------------------

    def create(self, payload: EmployeeCreate) -> Employee:
        self._check_manager(None, payload.manager_id)
        return self.employees.create(
            name=payload.name,
            role_title=payload.role_title,
            email=payload.email,
            slack_user_id=payload.slack_user_id,
            manager_id=payload.manager_id,
        )

    def update(self, employee_id: uuid.UUID, payload: EmployeeUpdate) -> Employee:
        employee = self.get_or_404(employee_id)
        values = payload.model_dump(exclude_unset=True)

        if "manager_id" in values:
            self._check_manager(employee_id, values["manager_id"])

        for key, value in values.items():
            setattr(employee, key, value)
        self.db.flush()
        return employee

    def create_login(self, employee_id: uuid.UUID, payload: EmployeeLoginCreate) -> User:
        employee = self.get_or_404(employee_id)
        if employee.user is not None:
            raise ConflictError("This employee already has a login account.")

        if find_user_for_login(self.db, payload.email) is not None:
            raise ConflictError("A user with that email address already exists.")

        user = self.users.create(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name or employee.name,
            role=UserRole.EMPLOYEE,
            employee_id=employee.id,
        )
        return user

    def update_login(self, employee_id: uuid.UUID, payload: EmployeeLoginUpdate) -> User:
        employee = self.get_or_404(employee_id)
        user = employee.user
        if user is None:
            raise NotFoundError("Login account not found for this employee.")

        values = payload.model_dump(exclude_unset=True)
        if "password" in values and values["password"]:
            user.password_hash = hash_password(values["password"])
        if "full_name" in values:
            user.full_name = values["full_name"]
        if "is_active" in values and values["is_active"] is not None:
            user.is_active = values["is_active"]

        self.db.flush()
        return user

    def delete_login(self, employee_id: uuid.UUID) -> None:
        employee = self.get_or_404(employee_id)
        user = employee.user
        if user is None:
            raise NotFoundError("Login account not found for this employee.")

        self.users.delete(user.id)
        self.db.flush()

    def delete(self, employee_id: uuid.UUID) -> None:
        """Refuse while they still owe something, and delete linked employee user account.

        The FK is ON DELETE SET NULL, so deleting would leave the tasks alive with no
        owner — and an owner-less task cannot be chased, so it drops out of the loop
        silently. Better to make the founder reassign or close them first.
        """
        employee = self.get_or_404(employee_id)

        open_tasks = self.tasks.list_filtered(
            statuses=OPEN_STATUSES, owner_employee_id=employee_id, limit=50
        )
        if open_tasks:
            raise ConflictError(
                "This employee still owns open tasks. Reassign or close them first.",
                details={
                    "open_task_count": len(open_tasks),
                    "tasks": [{"id": str(t.id), "title": t.title} for t in open_tasks[:10]],
                },
            )

        if employee.user is not None:
            if employee.user.role == UserRole.FOUNDER:
                raise ConflictError("Cannot delete an employee linked to a founder user account.")
            self.users.delete(employee.user.id)

        self.employees.delete(employee_id)

    # --- reads ------------------------------------------------------------------

    def list(
        self,
        *,
        search: str | None = None,
        unmapped: bool | None = None,
        manager_id: uuid.UUID | None = None,
    ) -> Sequence[Employee]:
        """All matches, never a best guess.

        A name query matching two people returns both. "Ask Mark" with two Marks has to
        surface as ambiguous — silently picking one is the failure this whole design
        avoids.
        """
        if unmapped:
            candidates = self.employees.list_unmapped()
        elif search:
            candidates = self.employees.search_by_name(search)
        else:
            candidates = self.employees.list(limit=500)

        if manager_id is not None:
            candidates = [e for e in candidates if e.manager_id == manager_id]
        return sorted(candidates, key=lambda e: e.name.lower())

    def reports_of(self, employee_id: uuid.UUID) -> Sequence[Employee]:
        return [e for e in self.employees.list(limit=500) if e.manager_id == employee_id]
