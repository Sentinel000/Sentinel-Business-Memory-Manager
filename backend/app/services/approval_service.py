"""The approval gate.

This is where the product's trust story lives: the AI drafts, a human decides, and the
decision is recorded with an author and a timestamp. Nothing reaches an employee
without passing through here.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.approval import Approval
from app.models.enums import ApprovalState, TaskStatus
from app.models.user import User
from app.repositories.approval import UNDECIDED_STATES, ApprovalRepository
from app.repositories.task import TaskRepository
from app.schemas.approval import ApprovalEditRequest
from app.services.base import TenantService

#: Once decided, an approval is final. Re-deciding would rewrite history.
DECIDED_STATES = (ApprovalState.APPROVED, ApprovalState.REJECTED)


class ApprovalService(TenantService):
    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        super().__init__(db, company_id)
        self.approvals = ApprovalRepository(db, company_id)
        self.tasks = TaskRepository(db, company_id)

    def get_or_404(self, approval_id: uuid.UUID) -> Approval:
        """404 for another company's approval — the repository is tenant-scoped."""
        approval = self.approvals.get_with_task(approval_id)
        if approval is None:
            raise NotFoundError("Approval not found.")
        return approval

    def _require_undecided(self, approval: Approval) -> None:
        if approval.state in DECIDED_STATES:
            raise ConflictError(
                f"This task was already {approval.state.value}.",
                details={
                    "state": approval.state.value,
                    "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                },
            )

    # --- decisions --------------------------------------------------------------

    def approve(self, approval_id: uuid.UUID, *, decided_by: User) -> Approval:
        """Release the task for delegation.

        When the extractor lands, this is also where the paused LangGraph run is
        resumed via ``approval.thread_id``. Today it only writes state — nothing here
        should make adding that harder.
        """
        approval = self.get_or_404(approval_id)
        self._require_undecided(approval)

        approval.state = ApprovalState.APPROVED
        approval.decided_by_user_id = decided_by.id
        approval.decided_at = datetime.now(UTC)
        approval.task.status = TaskStatus.APPROVED
        self.db.flush()
        return approval

    def edit(self, approval_id: uuid.UUID, payload: ApprovalEditRequest) -> Approval:
        """Apply changes and leave the task pending.

        Editing is not deciding. The founder can fix a wrong owner or deadline and
        still approve as a separate, explicit act. What they changed is recorded in
        edited_payload, so the trail shows the AI's proposal *and* the correction —
        which is also the signal for whether extraction is getting better.
        """
        approval = self.get_or_404(approval_id)
        self._require_undecided(approval)

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return approval

        task = approval.task
        before = {key: getattr(task, key) for key in changes}

        if "owner_employee_id" in changes:
            self.require_own_employee(changes["owner_employee_id"], field="employee")
        if "status" in changes:
            # Editing must not smuggle in a decision.
            changes.pop("status")

        for key, value in changes.items():
            setattr(task, key, value)

        approval.state = ApprovalState.EDITED
        approval.edited_payload = {
            "before": {k: _jsonable(v) for k, v in before.items()},
            "after": {k: _jsonable(v) for k, v in changes.items()},
        }
        self.db.flush()
        return approval

    def reject(
        self, approval_id: uuid.UUID, *, decided_by: User, reason: str | None = None
    ) -> Approval:
        approval = self.get_or_404(approval_id)
        self._require_undecided(approval)

        approval.state = ApprovalState.REJECTED
        approval.decided_by_user_id = decided_by.id
        approval.decided_at = datetime.now(UTC)
        approval.rejection_reason = reason
        approval.task.status = TaskStatus.REJECTED
        self.db.flush()
        return approval

    def bulk_approve(
        self, approval_ids: Sequence[uuid.UUID], *, decided_by: User
    ) -> tuple[list[uuid.UUID], list[dict[str, str]]]:
        """Approve several. One bad id does not fail the batch — it is reported.

        A queue of thirty after a long meeting is its own chore; this is the escape
        hatch once the founder trusts the extraction.
        """
        approved: list[uuid.UUID] = []
        skipped: list[dict[str, str]] = []

        for approval_id in approval_ids:
            try:
                self.approve(approval_id, decided_by=decided_by)
                approved.append(approval_id)
            except (NotFoundError, ConflictError) as exc:
                skipped.append({"id": str(approval_id), "reason": exc.message})

        return approved, skipped

    # --- reads ------------------------------------------------------------------

    def queue(
        self, *, states: Sequence[ApprovalState] | None = None
    ) -> tuple[Sequence[Approval], int]:
        """Everything still awaiting a decision, unless a state filter is given."""
        selected = states if states else UNDECIDED_STATES
        return (
            self.approvals.list_by_states(states=selected),
            self.approvals.count_by_states(selected),
        )


def _jsonable(value):
    """JSONB cannot hold a datetime or a UUID."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "value"):  # an enum
        return value.value
    return value
