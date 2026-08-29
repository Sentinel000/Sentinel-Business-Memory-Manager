"""StatusUpdate — the timeline. Append-only: who said what, when, and how.

This table is the accountability record. "Blocked for six days with no escalation"
is a query against it, not an argument.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReportedVia, TaskStatus, pg_enum

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.task import Task


class StatusUpdate(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "status_updates"
    __table_args__ = (Index("ix_status_updates_task_created", "task_id", "created_at"),)

    task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, "task_status", create_type=False),
        nullable=False,
    )

    #: Free text from the "Blocked" modal — the blocker reaches the founder with
    #: context rather than as a bare status.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    reported_by_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    reported_via: Mapped[ReportedVia] = mapped_column(
        pg_enum(ReportedVia, "reported_via"),
        nullable=False,
        server_default=ReportedVia.SLACK.value,
    )

    #: Slack message ts of the button click, so the same tap replayed is a no-op.
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    task: Mapped["Task"] = relationship(back_populates="status_updates")
    reported_by: Mapped["Employee | None"] = relationship()

    def __repr__(self) -> str:
        return f"<StatusUpdate {self.status.value} via={self.reported_via.value}>"
