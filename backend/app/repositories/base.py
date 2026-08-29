"""Tenant-scoped data access.

Row-level multi-tenancy is enforced here rather than in Postgres RLS. The trade is
deliberate: RLS is stronger, but it adds setup and fights connection pooling. Putting
the filter in a base class means no individual query *can* forget it — which is the
property that actually matters.

The one rule: a route handler never builds a query itself. It goes through a
repository constructed with a company_id taken from the signed JWT.
"""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    """Generic CRUD, permanently filtered to one company.

    Every read injects ``WHERE company_id = :company_id``; every write sets it.
    Subclasses add domain queries and inherit the scoping for free — see
    ``_scoped()``, which they should build on rather than starting from ``select()``.
    """

    model: type[ModelT]

    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id

    def _scoped(self):
        """The only entry point for a query. Always starts tenant-filtered."""
        return select(self.model).where(self.model.company_id == self.company_id)

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Fetch by primary key *within this tenant*.

        Returns None for a row belonging to another company, even when the id is
        correct. Guessing a valid UUID must not be enough to read someone else's data.
        """
        stmt = self._scoped().where(self.model.id == entity_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = self._scoped().limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    def count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.company_id == self.company_id)
        )
        return self.db.execute(stmt).scalar_one()

    def create(self, **values: Any) -> ModelT:
        """company_id is forced from the repository, never taken from the caller."""
        values.pop("company_id", None)
        instance = self.model(company_id=self.company_id, **values)
        self.db.add(instance)
        self.db.flush()
        return instance

    def update(self, entity_id: uuid.UUID, **values: Any) -> ModelT | None:
        instance = self.get(entity_id)
        if instance is None:
            return None
        values.pop("company_id", None)
        for key, value in values.items():
            setattr(instance, key, value)
        self.db.flush()
        return instance

    def delete(self, entity_id: uuid.UUID) -> bool:
        instance = self.get(entity_id)
        if instance is None:
            return False
        self.db.delete(instance)
        self.db.flush()
        return True
