"""Onboarding — turning a list of people into an org chart.

The structured half only. The LLM that produces this list from a pasted paragraph
comes later; this is what it will call.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.employee import Employee
from app.repositories.company import CompanyRepository
from app.repositories.task import TaskRepository
from app.schemas.onboarding import BulkEmployeeImport, ImportWarning
from app.services.base import TenantService


class OnboardingService(TenantService):
    def __init__(self, db: Session, company_id: uuid.UUID) -> None:
        super().__init__(db, company_id)
        self.companies = CompanyRepository(db)
        self.tasks = TaskRepository(db, company_id)

    def import_employees(
        self, payload: BulkEmployeeImport
    ) -> tuple[list[Employee], list[str], list[ImportWarning]]:
        """Create employees, then link managers by name.

        Two passes, because a paragraph naming Mark as reporting to Sarah does not
        guarantee Sarah appears first. Everyone exists before any manager is resolved.
        """
        created: list[Employee] = []
        skipped: list[str] = []
        warnings: list[ImportWarning] = []

        # Pass 1 — create. An existing name is skipped, not duplicated, so re-running
        # an import is safe.
        for row in payload.employees:
            name = row.name.strip()
            if self.employees.find_by_name(name):
                skipped.append(name)
                continue

            created.append(
                self.employees.create(
                    name=name,
                    role_title=row.role_title,
                    email=row.email,
                    slack_user_id=row.slack_user_id,
                )
            )

        self.db.flush()

        # Pass 2 — resolve managers.
        for row in payload.employees:
            if not row.manager:
                continue

            subject = self.employees.find_by_name(row.name.strip())
            if not subject:
                continue

            matches = self.employees.find_by_name(row.manager.strip())
            if not matches:
                # Partial match, for "Sarah" against "Sarah Chen".
                matches = self.employees.search_by_name(row.manager.strip())

            if not matches:
                warnings.append(
                    ImportWarning(
                        employee=row.name,
                        message=f"No employee named {row.manager!r} — manager not set.",
                    )
                )
                continue

            if len(matches) > 1:
                # Never guess. Two people called Sarah is exactly the ambiguity that
                # must reach the founder rather than being resolved silently.
                warnings.append(
                    ImportWarning(
                        employee=row.name,
                        message=(
                            f"{len(matches)} employees match {row.manager!r} — "
                            "manager not set, resolve it manually."
                        ),
                    )
                )
                continue

            manager = matches[0]
            if manager.id == subject[0].id:
                warnings.append(
                    ImportWarning(
                        employee=row.name, message="An employee cannot manage themselves."
                    )
                )
                continue

            subject[0].manager_id = manager.id

        self.db.flush()
        return created, skipped, warnings

    def status(self) -> dict:
        """What is configured and what is still missing."""
        company: Company | None = self.companies.get(self.company_id)
        everyone = self.employees.list(limit=1000)
        with_slack = [e for e in everyone if e.slack_user_id]
        persona = (company.persona_config or {}) if company else {}

        return {
            "company_id": self.company_id,
            "employee_count": len(everyone),
            "employees_with_slack": len(with_slack),
            "employees_without_slack": len(everyone) - len(with_slack),
            "slack_connected": bool(company and company.slack_bot_token),
            # A default-named assistant with no company context is not configured.
            "persona_configured": bool(persona.get("company_context")),
            "has_tasks": self.tasks.count() > 0,
        }
