"""Employee — the org chart and the target of a task.

Deliberately separate from User. Onboarding creates Mark from a pasted paragraph
before Mark has a login, and possibly before he ever gets one. Merging these two
tables is the change that forces a rewrite later.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.task import Task
    from app.models.user import User


class Employee(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        # Slack ids are unique per workspace; scoping by company keeps it per-tenant.
        UniqueConstraint("company_id", "slack_user_id", name="uq_employees_company_slack"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    role_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    #: Populated by the Slack member-list pull in step 2. Null until then, which is
    #: why task delegation must handle an unmapped owner rather than assume one.
    slack_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    #: Self-referential. Null for the top of the org chart. Read by the follow-up
    #: agent when a reminder times out and needs escalating.
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )

    company: Mapped["Company"] = relationship(back_populates="employees")
    manager: Mapped["Employee | None"] = relationship(
        remote_side="Employee.id", back_populates="reports"
    )
    reports: Mapped[list["Employee"]] = relationship(back_populates="manager")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner", foreign_keys="Task.owner_employee_id"
    )

    #: The optional login. The FK lives on users.employee_id — one direction only,
    #: so the two tables cannot disagree about who is linked to whom.
    user: Mapped["User | None"] = relationship(back_populates="employee", uselist=False)

    def __repr__(self) -> str:
        return f"<Employee {self.name!r}>"
