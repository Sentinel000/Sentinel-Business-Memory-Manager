"""Domain enums, stored as native Postgres enum types."""

import enum
from typing import Any

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str, **kwargs: Any) -> SAEnum:
    """A native Postgres enum storing the member *value*, not its Python name.

    SQLAlchemy defaults to persisting ``member.name`` — which would put
    ``'PENDING_APPROVAL'`` in the column while our server defaults say
    ``'pending_approval'``, and every insert relying on the default would fail.
    values_callable is what keeps the two halves in agreement.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda cls: [member.value for member in cls],
        **kwargs,
    )


class UserRole(str, enum.Enum):
    """Two roles, checked by a dependency. No RBAC tables — see the plan."""

    FOUNDER = "founder"
    EMPLOYEE = "employee"


class TaskStatus(str, enum.Enum):
    """A task's lifecycle.

    PENDING_APPROVAL is the server-side default. Nothing may create a task in any
    other state — the trust story cannot depend on the model remembering to ask.
    """

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    REJECTED = "rejected"
    OVERDUE = "overdue"


class ApprovalState(str, enum.Enum):
    """Founder's decision on an extracted task."""

    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class ReportedVia(str, enum.Enum):
    """How a status update reached us."""

    SLACK = "slack"
    DASHBOARD = "dashboard"
    AGENT = "agent"
