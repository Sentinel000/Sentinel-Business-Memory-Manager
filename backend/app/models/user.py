"""User — login identity only.

A founder is a User with role=founder and usually no Employee row.
An employee is an Employee row that may later gain a User.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole, pg_enum

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.employee import Employee


class User(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Email is globally unique so login is deterministic across tenants.
        UniqueConstraint("email", name="uq_users_email"),
        # Enforces 1:1 link with Employee. Nulls allowed for founders.
        UniqueConstraint("employee_id", name="uq_users_employee_id"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
        server_default=UserRole.EMPLOYEE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    #: The only FK between users and employees. Null for founders.
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )

    company: Mapped["Company"] = relationship(back_populates="users")
    employee: Mapped["Employee | None"] = relationship(back_populates="user")

    @validates("email")
    def validate_email(self, key: str, value: str) -> str:
        return value.lower().strip()

    def __repr__(self) -> str:
        # Never include the hash. See docs/rules/security.md.
        return f"<User {self.email!r} role={self.role.value}>"
