"""Authentication routes."""

import logging

from fastapi import APIRouter

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.knowledge.provisioning import ensure_knowledge_database
from app.dependencies import CurrentUser, DbSession
from app.exceptions import InactiveUserError, InvalidCredentialsError, NotFoundError
from app.models.enums import UserRole
from app.repositories.company import CompanyRepository
from app.repositories.user import UserRepository, find_user_for_login
from app.schemas.auth import CurrentUserResponse, LoginRequest, SignupRequest, TokenResponse
from app.schemas.company import PersonaConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: DbSession) -> TokenResponse:
    """Self-provision a company tenant and founder user account.

    Initializes persona_config.company_context with the provided company description
    and issues an access token for immediate authenticated onboarding.
    """
    persona_config = PersonaConfig(company_context=payload.company_description)

    company_repo = CompanyRepository(db)
    company = company_repo.create(
        name=payload.company_name,
        industry=payload.industry,
        persona_config=persona_config.model_dump(),
    )

    user_repo = UserRepository(db, company_id=company.id)
    user = user_repo.create(
        email=payload.founder_email,
        password_hash=hash_password(payload.founder_password),
        full_name=payload.founder_full_name,
        role=UserRole.FOUNDER,
    )

    db.commit()

    # Knowledge memory is provisioned here so the dashboard reports it connected from
    # the first login. Failure is non-fatal: the extractor provisions lazily too.
    ensure_knowledge_database(db, company)

    token = create_access_token(
        user_id=user.id, company_id=company.id, role=user.role
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


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
