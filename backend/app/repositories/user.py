"""User data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import TenantScopedRepository


class UserRepository(TenantScopedRepository[User]):
    model = User

    def find_by_email(self, email: str) -> User | None:
        """Within this tenant."""
        stmt = self._scoped().where(User.email == email.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()


def find_user_for_login(db: Session, email: str) -> User | None:
    """Cross-tenant lookup used only at login, before a company is known.

    Deliberately not a repository method: this is the one query that cannot be
    tenant-scoped, because resolving the tenant is its whole purpose. It reads a
    single user by email and nothing else. Everything downstream uses the
    company_id it returns.
    """
    stmt = select(User).where(User.email == email.lower().strip())
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: uuid.UUID, company_id: uuid.UUID) -> User | None:
    """Load the token's subject, checking it still belongs to the token's company."""
    stmt = select(User).where(User.id == user_id, User.company_id == company_id)
    return db.execute(stmt).scalar_one_or_none()
