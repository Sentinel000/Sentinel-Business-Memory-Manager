"""Employee data access."""

import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import func

from app.models.employee import Employee
from app.repositories.base import TenantScopedRepository


class EmployeeRepository(TenantScopedRepository[Employee]):
    model = Employee

    def find_by_slack_user_id(self, slack_user_id: str) -> Employee | None:
        stmt = self._scoped().where(Employee.slack_user_id == slack_user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def find_by_name(self, name: str) -> Sequence[Employee]:
        """Case-insensitive name match for owner resolution.

        Returns *all* matches on purpose. "Ask Mark" with two Marks must surface the
        ambiguity so it can be flagged, never silently resolved to one of them.
        """
        stmt = self._scoped().where(func.lower(Employee.name) == name.lower().strip())
        return self.db.execute(stmt).scalars().all()

    def search_by_name(self, fragment: str) -> Sequence[Employee]:
        """Partial match, for a first-name mention against a full-name record."""
        stmt = self._scoped().where(Employee.name.ilike(f"%{fragment.strip()}%"))
        return self.db.execute(stmt).scalars().all()

    def get_many(self, employee_ids: Collection[uuid.UUID]) -> Sequence[Employee]:
        """Several employees by id, in one tenant-scoped query.

        Used to resolve owner names for a task list without a query per row. Ids from
        another company simply do not come back.
        """
        if not employee_ids:
            return []
        stmt = self._scoped().where(Employee.id.in_(list(employee_ids)))
        return self.db.execute(stmt).scalars().all()

    def list_unmapped(self) -> Sequence[Employee]:
        """Employees with no Slack id yet — they cannot be delegated to."""
        stmt = self._scoped().where(Employee.slack_user_id.is_(None))
        return self.db.execute(stmt).scalars().all()
