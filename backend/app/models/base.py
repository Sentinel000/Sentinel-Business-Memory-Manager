"""Declarative base and the mixins every model is built from.

TenantMixin is load-bearing: it is what makes row-level multi-tenancy structural
rather than something each query has to remember. Every model except Company
inherits it.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base. Alembic autogenerate reads Base.metadata."""


class UUIDPrimaryKeyMixin:
    """UUID primary keys, generated application-side so a row has its id before flush."""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at / updated_at, maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """The tenancy boundary.

    company_id is non-null and indexed on every tenant-owned table. It is set from
    the signed JWT claim, never from a request body — see app/dependencies.py.
    Queries must reach it through TenantScopedRepository, which injects the filter
    so no individual query can forget it.
    """

    @declared_attr
    def company_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
