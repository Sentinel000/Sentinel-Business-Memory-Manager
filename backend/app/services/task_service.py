"""Task business logic.

Routes stay thin — validate, delegate, return. The rules live here:

* a founder-created task is approved at creation, with a real approval row
* an owner must belong to the caller's company
* the timeline is append-only
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.approval import Approval
from app.models.enums import ApprovalState, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.task import TaskRepository
from app.schemas.task import StatusUpdateCreate, TaskCreate, TaskUpdate
from app.services.base import TenantService


class TaskService(TenantService):
    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        super().__init__(db, company_id)
        self.tasks = TaskRepository(db, company_id)

    # --- helpers ----------------------------------------------------------------

    def get_or_404(self, task_id: uuid.UUID) -> Task:
        """404, not 403, for another company's task.

        403 would confirm the row exists. Across a tenant boundary the correct answer
        is that it does not exist, as far as this caller is concerned.
        """
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.")
        return task

    def get_owned_or_404(self, task_id: uuid.UUID, employee_id: uuid.UUID) -> Task:
        """Load a task and verify that employee_id owns it.

        Returns 404 (not 403) on owner mismatch to avoid disclosing task existence.
        """
        task = self.get_or_404(task_id)
        if task.owner_employee_id != employee_id:
            raise NotFoundError("Task not found.")
        return task

    # --- commands ---------------------------------------------------------------

    def create_manual(
        self, payload: TaskCreate, *, created_by: User, idempotency_key: str | None = None
    ) -> tuple[Task, bool]:
        """Create a task the founder typed. Returns ``(task, created)``.

        Approved at creation, because the founder *is* the approval step — but the
        promotion is recorded as a real approval row rather than the task simply
        appearing pre-blessed. Rule 1 holds: nothing reaches an employee without a
        human decision, and the decision has an author and a timestamp.

        The schema default stays pending_approval, untouched. When the extractor
        writes through this service in step 5 it will skip the promotion, and its
        tasks will fall to that default and wait.
        """
        self.require_own_employee(payload.owner_employee_id, field="employee")

        key = idempotency_key or f"manual:{uuid.uuid4()}"
        existing = self.tasks.find_by_idempotency_key(key)
        if existing is not None:
            # A double-clicked Create button. Return what already exists.
            return existing, False

        task = self.tasks.create(
            title=payload.title,
            description=payload.description,
            owner_employee_id=payload.owner_employee_id,
            deadline=payload.deadline,
            idempotency_key=key,
            status=TaskStatus.APPROVED,
            created_by_agent=None,
        )

        self.db.add(
            Approval(
                company_id=self.company_id,
                task_id=task.id,
                state=ApprovalState.APPROVED,
                decided_by_user_id=created_by.id,
                decided_at=datetime.now(UTC),
            )
        )
        self.db.flush()
        return task, True

    def create_pending(
        self,
        *,
        title: str,
        idempotency_key: str,
        source_quote: str,
        source_ref: str | None = None,
        source_id: str | None = None,
        description: str | None = None,
        owner_employee_id: uuid.UUID | None = None,
        deadline: datetime | None = None,
        confidence: float | None = None,
        created_by_agent: str = "extractor",
        thread_id: str | None = None,
    ) -> tuple[Task, bool]:
        """Create a task that must be approved before anyone is contacted.

        The agent path. Unlike create_manual there is **no promotion**: the task falls
        to the schema's pending_approval default and an approval row is written in
        `pending`. That is rule 1 — the AI drafts, a human decides.

        source_quote is required here rather than optional, because rule 6 applies to
        anything the AI produces. A founder can type a task with no citation; an agent
        cannot.

        Returns ``(task, created)``. Re-running an extraction over the same input
        returns the existing task untouched rather than duplicating it or reverting a
        founder's edits.
        """
        self.require_own_employee(owner_employee_id, field="employee")

        existing = self.tasks.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False

        task = self.tasks.create(
            title=title,
            description=description,
            owner_employee_id=owner_employee_id,
            deadline=deadline,
            idempotency_key=idempotency_key,
            source_quote=source_quote,
            source_ref=source_ref,
            source_id=source_id,
            confidence=confidence,
            created_by_agent=created_by_agent,
            # status is deliberately not passed — it falls to the server default.
        )

        self.db.add(
            Approval(
                company_id=self.company_id,
                task_id=task.id,
                state=ApprovalState.PENDING,
                thread_id=thread_id,
            )
        )
        self.db.flush()
        return task, True

    #: Founder edits that constitute a genuinely new commitment cycle, and so earn
    #: the task a fresh chase budget. A title or description fix does not — the
    #: person still owes the same thing by the same date.
    _CHASE_RESETTING_FIELDS = ("status", "owner_employee_id", "deadline")

    def update(self, task_id: uuid.UUID, payload: TaskUpdate) -> Task:
        task = self.get_or_404(task_id)
        values = payload.model_dump(exclude_unset=True)

        if "owner_employee_id" in values:
            self.require_own_employee(values["owner_employee_id"], field="employee")

        # Compared before the writes, and by value: a payload that merely echoes the
        # current owner is not a reassignment, and must not restart the ladder.
        reactivated = any(
            field in values and values[field] != getattr(task, field)
            for field in self._CHASE_RESETTING_FIELDS
        )

        for key, value in values.items():
            setattr(task, key, value)

        if reactivated:
            # The founder unblocked, reassigned, or moved the date — the situation
            # changed, so the owner should not inherit a spent budget for a blocker
            # that was legitimate.
            task.chase_count = 0
            task.escalated = False
            task.last_chased_at = None

        self.db.flush()
        return task

    def record_status(self, task_id: uuid.UUID, payload: StatusUpdateCreate) -> Task:
        """Append a timeline entry and move the task to that status.

        Two writes on purpose: status_updates is the history, tasks.status is the
        current state. Neither is derivable from the other cheaply enough to drop.
        """
        task = self.get_or_404(task_id)
        self.require_own_employee(payload.reported_by_employee_id, field="employee")

        self.tasks.add_status_update(
            task=task,
            status=payload.status,
            note=payload.note,
            reported_by_employee_id=payload.reported_by_employee_id,
            reported_via=payload.reported_via,
        )
        task.status = payload.status

        # A report is a response, and a response is what chasing was asking for.
        # `escalated` means "waiting on the founder", so it tracks the answer:
        # blocked hands the task over, anything active hands it back.
        #
        # `chase_count` deliberately does NOT reset here. Only a founder action
        # grants a fresh budget — otherwise marking oneself blocked and then in
        # progress would mint unlimited chases. Silence after a response is caught
        # by the report's quiet section, which reads the timeline, not the counter.
        if payload.status is TaskStatus.BLOCKED:
            task.escalated = True
        elif payload.status in (TaskStatus.IN_PROGRESS, TaskStatus.DONE):
            task.escalated = False

        self.db.flush()
        return task

    def delete(self, task_id: uuid.UUID) -> None:
        self.get_or_404(task_id)
        self.tasks.delete(task_id)

    # --- reads ------------------------------------------------------------------

    def owner_names(self, tasks) -> dict[uuid.UUID, str]:
        """Resolve owner ids to names in one query, not one per task."""
        owner_ids = {t.owner_employee_id for t in tasks if t.owner_employee_id}
        return {e.id: e.name for e in self.employees.get_many(owner_ids)}
