"""Task data access.

Every query starts from ``self._scoped()`` so the company filter is applied before
anything else. See app/repositories/base.py for why that matters.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select

from app.models.enums import TaskStatus
from app.models.status_update import StatusUpdate
from app.models.task import Task
from app.repositories.base import TenantScopedRepository

#: A task in one of these is finished — it is never overdue and never chased.
TERMINAL_STATUSES = (TaskStatus.DONE, TaskStatus.REJECTED)

SORTABLE = {"deadline": Task.deadline, "created_at": Task.created_at, "title": Task.title}


class TaskRepository(TenantScopedRepository[Task]):
    model = Task

    def list_filtered(
        self,
        *,
        statuses: Sequence[TaskStatus] | None = None,
        owner_employee_id: uuid.UUID | None = None,
        overdue: bool | None = None,
        search: str | None = None,
        sort: str = "created_at",
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Task]:
        stmt = self._apply_filters(
            self._scoped(),
            statuses=statuses,
            owner_employee_id=owner_employee_id,
            overdue=overdue,
            search=search,
        )

        column = SORTABLE.get(sort, Task.created_at)
        # Nulls last either way: a task with no deadline should not head the list.
        stmt = stmt.order_by(column.desc().nullslast() if descending else column.asc().nullslast())
        return self.db.execute(stmt.limit(limit).offset(offset)).scalars().all()

    def count_filtered(
        self,
        *,
        statuses: Sequence[TaskStatus] | None = None,
        owner_employee_id: uuid.UUID | None = None,
        overdue: bool | None = None,
        search: str | None = None,
    ) -> int:
        """Total matching rows, for the pagination header."""
        stmt = self._apply_filters(
            select(func.count()).select_from(Task).where(Task.company_id == self.company_id),
            statuses=statuses,
            owner_employee_id=owner_employee_id,
            overdue=overdue,
            search=search,
        )
        return self.db.execute(stmt).scalar_one()

    def _apply_filters(
        self,
        stmt,
        *,
        statuses: Sequence[TaskStatus] | None,
        owner_employee_id: uuid.UUID | None,
        overdue: bool | None,
        search: str | None,
    ):
        if statuses:
            stmt = stmt.where(Task.status.in_(statuses))
        if owner_employee_id is not None:
            stmt = stmt.where(Task.owner_employee_id == owner_employee_id)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
        if overdue is not None:
            # Derived from the deadline rather than stored, so it can never be stale.
            past_due = (
                Task.deadline.is_not(None)
                & (Task.deadline < datetime.now(UTC))
                & Task.status.notin_(TERMINAL_STATUSES)
            )
            stmt = stmt.where(past_due if overdue else ~past_due)
        return stmt

    def find_by_idempotency_key(self, key: str) -> Task | None:
        return self.db.execute(
            self._scoped().where(Task.idempotency_key == key)
        ).scalar_one_or_none()

    def upsert_by_idempotency_key(self, key: str, **values) -> tuple[Task, bool]:
        """Get-or-create on the idempotency key. Returns ``(task, created)``.

        Rule 3: re-running an agent must never duplicate a task. An existing row is
        returned untouched rather than overwritten — a founder may have edited it
        since, and a re-extraction should not silently revert that.
        """
        existing = self.find_by_idempotency_key(key)
        if existing is not None:
            return existing, False
        return self.create(idempotency_key=key, **values), True

    def list_stale(self, *, older_than_days: int, limit: int = 100) -> Sequence[Task]:
        """Delegated tasks with no recent chase — the follow-up agent's input.

        Written now because the query belongs with the others; the agent that calls it
        arrives in step 6.
        """
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        stmt = (
            self._scoped()
            .where(
                Task.status.notin_(TERMINAL_STATUSES),
                Task.delegated_at.is_not(None),
                or_(Task.last_chased_at.is_(None), Task.last_chased_at < cutoff),
            )
            .order_by(Task.deadline.asc().nullslast())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def list_pending_approval(self, *, limit: int = 100) -> Sequence[Task]:
        stmt = (
            self._scoped()
            .where(Task.status == TaskStatus.PENDING_APPROVAL)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def add_status_update(
        self,
        *,
        task: Task,
        status: TaskStatus,
        note: str | None = None,
        reported_by_employee_id: uuid.UUID | None = None,
        reported_via,
        idempotency_key: str | None = None,
    ) -> StatusUpdate:
        """Append to the timeline. The caller moves ``task.status`` separately.

        The timeline is append-only: it is the accountability record, so a correction
        is a new row, never an edit to an old one.
        """
        update = StatusUpdate(
            company_id=self.company_id,
            task_id=task.id,
            status=status,
            note=note,
            reported_by_employee_id=reported_by_employee_id,
            reported_via=reported_via,
            idempotency_key=idempotency_key,
        )
        self.db.add(update)
        self.db.flush()
        return update
