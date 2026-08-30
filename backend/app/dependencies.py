"""FastAPI dependencies: authentication, tenant resolution, role checks.

get_current_user is where the tenancy boundary is drawn. company_id comes from the
signed token and nowhere else — never a request body, query param, or header.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.exceptions import ForbiddenError, InactiveUserError, NotAuthenticatedError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.company import CompanyRepository
from app.repositories.approval import ApprovalRepository
from app.repositories.employee import EmployeeRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository, get_user_by_id
from app.services.approval_service import ApprovalService
from app.services.employee_service import EmployeeService
from app.services.onboarding_service import OnboardingService
from app.services.task_service import TaskService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    """Decode the token and load its subject.

    The user is re-checked against the token's company_id, so a token that survives
    a user being moved between tenants stops working rather than following them.
    """
    if not token:
        raise NotAuthenticatedError()

    claims = decode_access_token(token)
    if claims is None:
        raise NotAuthenticatedError("Your session is invalid or has expired.")

    try:
        user_id = uuid.UUID(claims["sub"])
        company_id = uuid.UUID(claims["company_id"])
    except (KeyError, ValueError):
        raise NotAuthenticatedError("Your session is invalid or has expired.") from None

    user = get_user_by_id(db, user_id, company_id)
    if user is None:
        raise NotAuthenticatedError("Your session is invalid or has expired.")
    if not user.is_active:
        raise InactiveUserError()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_company_id(current_user: CurrentUser) -> uuid.UUID:
    """The tenant for this request. Always derived from the authenticated user."""
    return current_user.company_id


CompanyId = Annotated[uuid.UUID, Depends(get_company_id)]


def require_founder(current_user: CurrentUser) -> User:
    """Founder-only routes. Two roles, one check — no RBAC tables."""
    if current_user.role is not UserRole.FOUNDER:
        raise ForbiddenError("This action is restricted to founders.")
    return current_user


FounderUser = Annotated[User, Depends(require_founder)]


def require_employee(current_user: CurrentUser) -> User:
    """Employee-only routes."""
    if current_user.role is not UserRole.EMPLOYEE or current_user.employee_id is None:
        raise ForbiddenError("This action is restricted to employees.")
    return current_user


EmployeeUser = Annotated[User, Depends(require_employee)]


def get_current_employee_id(employee_user: EmployeeUser) -> uuid.UUID:
    """Return the employee_id of the authenticated employee user."""
    return employee_user.employee_id  # type: ignore[return-value]


CurrentEmployeeId = Annotated[uuid.UUID, Depends(get_current_employee_id)]


# --- Tenant-scoped repositories -------------------------------------------------
# Routes take these rather than a bare session, so the company filter is applied
# before a handler can write a query.


def get_user_repository(db: DbSession, company_id: CompanyId) -> UserRepository:
    return UserRepository(db, company_id)


def get_employee_repository(db: DbSession, company_id: CompanyId) -> EmployeeRepository:
    return EmployeeRepository(db, company_id)


def get_company_repository(db: DbSession) -> CompanyRepository:
    return CompanyRepository(db)


def get_task_repository(db: DbSession, company_id: CompanyId) -> TaskRepository:
    return TaskRepository(db, company_id)


def get_task_service(db: DbSession, company_id: CompanyId) -> TaskService:
    return TaskService(db, company_id)


def get_approval_repository(db: DbSession, company_id: CompanyId) -> ApprovalRepository:
    return ApprovalRepository(db, company_id)


def get_employee_service(db: DbSession, company_id: CompanyId) -> EmployeeService:
    return EmployeeService(db, company_id)


def get_approval_service(db: DbSession, company_id: CompanyId) -> ApprovalService:
    return ApprovalService(db, company_id)


def get_onboarding_service(db: DbSession, company_id: CompanyId) -> OnboardingService:
    return OnboardingService(db, company_id)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
EmployeeRepo = Annotated[EmployeeRepository, Depends(get_employee_repository)]
CompanyRepo = Annotated[CompanyRepository, Depends(get_company_repository)]
TaskRepo = Annotated[TaskRepository, Depends(get_task_repository)]
TaskSvc = Annotated[TaskService, Depends(get_task_service)]
ApprovalRepo = Annotated[ApprovalRepository, Depends(get_approval_repository)]
EmployeeSvc = Annotated[EmployeeService, Depends(get_employee_service)]
ApprovalSvc = Annotated[ApprovalService, Depends(get_approval_service)]
OnboardingSvc = Annotated[OnboardingService, Depends(get_onboarding_service)]
