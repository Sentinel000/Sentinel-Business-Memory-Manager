"""Approval data access."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import joinedload

from app.models.approval import Approval
from app.models.enums import ApprovalState
from app.repositories.base import TenantScopedRepository


#: Still waiting on the founder. EDITED belongs here: editing is not deciding, so an
#: edited task stays in the queue - visibly touched, but undecided.
UNDECIDED_STATES = (ApprovalState.PENDING, ApprovalState.EDITED)


class ApprovalRepository(TenantScopedRepository[Approval]):
    model = Approval

    def list_by_states(
        self, *, states: Sequence[ApprovalState] | None = None, limit: int = 100
    ) -> Sequence[Approval]:
        """The queue. Oldest first - the founder works a backlog in order.

        None means every state; the default is whatever is still undecided.
        """
        stmt = self._scoped().options(joinedload(Approval.task))
        if states:
            stmt = stmt.where(Approval.state.in_(states))
        stmt = stmt.order_by(Approval.created_at.asc()).limit(limit)
        return self.db.execute(stmt).unique().scalars().all()

    def count_by_states(self, states: Sequence[ApprovalState] | None = None) -> int:
        from sqlalchemy import func, select

        stmt = (
            select(func.count())
            .select_from(Approval)
            .where(Approval.company_id == self.company_id)
        )
        if states:
            stmt = stmt.where(Approval.state.in_(states))
        return self.db.execute(stmt).scalar_one()

    def get_with_task(self, approval_id: uuid.UUID) -> Approval | None:
        stmt = (
            self._scoped()
            .options(joinedload(Approval.task))
            .where(Approval.id == approval_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def find_by_task(self, task_id: uuid.UUID) -> Approval | None:
        return self.db.execute(
            self._scoped().where(Approval.task_id == task_id)
        ).scalar_one_or_none()
