"""Shared service behaviour.

The guard below is the one every service needs: a foreign key proves a row exists, it
does not prove the row is *yours*. Any id arriving in a request body has to be resolved
through a tenant-scoped repository before it is written.
"""

import uuid

from sqlalchemy.orm import Session

from app.exceptions import ValidationError
from app.models.employee import Employee
from app.repositories.employee import EmployeeRepository


class TenantService:
    """Base for services that act within one company."""

    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self.employees = EmployeeRepository(db, company_id)

    def require_own_employee(
        self, employee_id: uuid.UUID | None, *, field: str = "employee"
    ) -> Employee | None:
        """Resolve an employee id, rejecting one from another company.

        The employee repository is tenant-scoped, so a foreign id comes back None and
        is indistinguishable from a nonexistent one — which is the correct answer to
        give a caller who should not know it exists.
        """
        if employee_id is None:
            return None
        employee = self.employees.get(employee_id)
        if employee is None:
            raise ValidationError(f"That {field} does not exist in this company.")
        return employee
