"""Auth API contracts."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the token expires.")


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    #: Assistant identity, so the dashboard can render the configured name and tone.
    persona_config: dict = {}


class CurrentUserResponse(BaseModel):
    """The authenticated user. Never carries password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    company_id: uuid.UUID
    employee_id: uuid.UUID | None = None
    company: CompanySummary
