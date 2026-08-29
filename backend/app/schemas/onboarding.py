"""Onboarding contracts.

Managers are referenced **by name**, not by id, because that is what the LLM will emit
when the paste-a-paragraph step lands. Building the endpoint this way now means that
feature is a parser in front of something that already works.
"""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.employee import EmployeeSummary


class EmployeeImport(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role_title: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    slack_user_id: str | None = Field(default=None, max_length=64)
    #: The manager's *name*. Resolved in a second pass, after everyone exists.
    manager: str | None = Field(default=None, max_length=200)


class BulkEmployeeImport(BaseModel):
    employees: list[EmployeeImport] = Field(min_length=1, max_length=500)


class ImportWarning(BaseModel):
    employee: str
    message: str


class BulkImportResponse(BaseModel):
    created: list[EmployeeSummary]
    #: Already existed by name, so left alone rather than duplicated.
    skipped: list[str] = []
    #: An unresolvable or ambiguous manager name. Reported instead of failing the
    #: import — a founder should not lose 24 good rows to one typo.
    warnings: list[ImportWarning] = []


class OnboardingStatus(BaseModel):
    """What the dashboard's setup checklist renders."""

    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    employee_count: int
    employees_with_slack: int
    employees_without_slack: int
    slack_connected: bool
    persona_configured: bool
    has_tasks: bool

    @property
    def is_ready(self) -> bool:
        return self.employee_count > 0 and self.slack_connected
