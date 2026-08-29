"""Approval — the human gate between extraction and anyone being contacted.

The AI never messages the team on its own. Every extracted task waits here.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApprovalState, pg_enum

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Approval(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "approvals"

    task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    state: Mapped[ApprovalState] = mapped_column(
        pg_enum(ApprovalState, "approval_state"),
        nullable=False,
        server_default=ApprovalState.PENDING.value,
        index=True,
    )

    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: What the founder changed, when the decision was "edited". Kept alongside the
    #: task rather than only applied to it, so the audit trail shows the original.
    edited_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: LangGraph checkpoint thread. Approving resumes the paused run rather than
    #: starting a new one — this is why the interrupt survives a restart.
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    task: Mapped["Task"] = relationship(back_populates="approval")
    decided_by: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Approval state={self.state.value}>"
