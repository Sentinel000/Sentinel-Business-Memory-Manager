"""Company data access.

Company is the tenant root and has no company_id of its own, so it does not use
TenantScopedRepository. Access is by the id from the token.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, company_id: uuid.UUID) -> Company | None:
        return self.db.execute(
            select(Company).where(Company.id == company_id)
        ).scalar_one_or_none()

    def create(self, name: str, **values: object) -> Company:
        company = Company(name=name, **values)
        self.db.add(company)
        self.db.flush()
        return company
