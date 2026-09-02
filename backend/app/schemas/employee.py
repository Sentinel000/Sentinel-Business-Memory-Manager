"""Employee API contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role_title: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    slack_user_id: str | None = Field(default=None, max_length=64)
    manager_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be blank.")
        return cleaned


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role_title: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    slack_user_id: str | None = Field(default=None, max_length=64)
    manager_id: uuid.UUID | None = None


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role_title: str | None
    slack_user_id: str | None
    manager_id: uuid.UUID | None
    #: Whether this person has a dashboard login. Carried on the summary too, so the
    #: roster can render credential state without a per-row detail fetch.
    has_login: bool = False

    @property
    def is_slack_mapped(self) -> bool:
        return self.slack_user_id is not None


class EmployeeDetail(EmployeeSummary):
    email: EmailStr | None
    created_at: datetime
    updated_at: datetime
    manager: EmployeeSummary | None = None
    #: Direct reports, so the dashboard can render the org chart one level at a time.
    reports: list[EmployeeSummary] = []


class EmployeeListResponse(BaseModel):
    items: list[EmployeeSummary]
    total: int


class EmployeeLoginCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class EmployeeLoginUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = None
    is_active: bool | None = None


class EmployeeLoginRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    role: UserRole
    employee_id: uuid.UUID
