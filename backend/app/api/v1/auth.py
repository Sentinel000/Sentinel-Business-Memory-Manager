"""Authentication routes."""

import logging

from fastapi import APIRouter

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.dependencies import CurrentUser, DbSession
from app.exceptions import InactiveUserError, InvalidCredentialsError, NotFoundError
from app.repositories.company import CompanyRepository
from app.repositories.user import find_user_for_login
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    """Exchange credentials for a token carrying the user's company_id.

    The same error is returned for an unknown email and a wrong password, so the
    response cannot be used to enumerate accounts.
    """
    user = find_user_for_login(db, payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        # Log the attempt, never the password. See docs/rules/security.md.
        logger.info("Failed login attempt for %s", payload.email)
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    token = create_access_token(
        user_id=user.id, company_id=user.company_id, role=user.role
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(current_user: CurrentUser, db: DbSession) -> CurrentUserResponse:
    """The authenticated user and their company."""
    company = CompanyRepository(db).get(current_user.company_id)
    if company is None:
        # The token referenced a company that no longer exists.
        raise NotFoundError("Company not found.")

    return CurrentUserResponse.model_validate(
        {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "company_id": current_user.company_id,
            "employee_id": current_user.employee_id,
            "company": company,
        }
    )
