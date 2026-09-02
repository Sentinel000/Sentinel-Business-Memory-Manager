"""Task — the row everything else hangs off.

Three of the project's non-negotiable rules are enforced here as schema constraints
rather than as application code, because a constraint cannot be forgotten and a
convention can.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TaskStatus, pg_enum

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.employee import Employee
    from app.models.status_update import StatusUpdate


class Task(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        # Rule 3: re-running an agent must never duplicate a task. The key is derived
        # from (source_id, title); this constraint is what makes upsert possible.
        # Scoped by company so two tenants can extract from identical text.
        UniqueConstraint("company_id", "idempotency_key", name="uq_tasks_company_idempotency"),
        # The follow-up agent's hot path: open tasks for one tenant, by deadline.
        Index("ix_tasks_company_status_deadline", "company_id", "status", "deadline"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: Rule 1: the server default. create_task() can only produce pending_approval —
    #: it is not a value the model chooses. Anything that wants a different initial
    #: state has to go through the approval flow.
    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, "task_status"),
        nullable=False,
        server_default=TaskStatus.PENDING_APPROVAL.value,
        index=True,
    )

    #: Rule 6: every task cites its source verbatim. Nullable only so a founder can
    #: type a task by hand; agent-created rows must always carry the quote, which the
    #: tool layer enforces.
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Human-readable provenance, e.g. "Sales Standup, Tue 10:04".
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Points at the transcript in the knowledge layer (step 7).
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Extractor's owner-resolution confidence, 0..1. Low values route to the queue
    #: rather than being guessed at — "ask Mark" must never silently pick a Mark.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: Which agent wrote this, or null for manual creation.
    created_by_agent: Mapped[str | None] = mapped_column(String(64), nullable=True)

    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Set once the delegation DM has gone out, so a re-run does not message twice.
    delegated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_chased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: Reminders sent so far, against the company's ``max_chases``.
    #:
    #: Only a *founder* action resets this to zero — unblocking, reassigning, or
    #: moving the deadline. An employee marking themselves in progress restarts the
    #: silence clock but not the budget, so "mark blocked to buy time" cannot mint a
    #: fresh set of chases.
    chase_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    #: Chasing has stopped and the task is waiting on the founder. Previously meant
    #: "the manager was DM'd"; with Slack gone the founder *is* the escalation path,
    #: so it now means "handed back" — set when the chase limit is reached or the
    #: owner reports a blocker.
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    owner: Mapped["Employee | None"] = relationship(
        back_populates="tasks", foreign_keys=[owner_employee_id]
    )
    status_updates: Mapped[list["StatusUpdate"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="StatusUpdate.created_at"
    )
    approval: Mapped["Approval | None"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Task {self.title!r} status={self.status.value}>"
