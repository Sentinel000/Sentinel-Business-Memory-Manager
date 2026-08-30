"""Onboarding routes — the structured half of company setup."""

from fastapi import APIRouter

from app.dependencies import DbSession, FounderUser, OnboardingSvc
from app.schemas.employee import EmployeeSummary
from app.schemas.onboarding import BulkEmployeeImport, BulkImportResponse, OnboardingStatus

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/employees/bulk", response_model=BulkImportResponse)
def import_employees(
    payload: BulkEmployeeImport, service: OnboardingSvc, _: FounderUser, db: DbSession
) -> BulkImportResponse:
    """Import an org chart in one call.

    Managers are given by name and resolved in a second pass, so the input does not
    have to be ordered. An unresolvable or ambiguous name becomes a warning rather
    than an error — one typo should not cost the other twenty-four rows.

    This is the endpoint the paste-a-paragraph feature will call once the LLM turns
    prose into this list.
    """
    created, skipped, warnings = service.import_employees(payload)
    db.commit()

    return BulkImportResponse(
        created=[EmployeeSummary.model_validate(e) for e in created],
        skipped=skipped,
        warnings=warnings,
    )


@router.get("/status", response_model=OnboardingStatus)
def onboarding_status(service: OnboardingSvc, _: FounderUser) -> OnboardingStatus:
    """What is configured and what is still missing — the setup checklist.

    `employees_without_slack` is the one that matters operationally: those people
    cannot be delegated to, so a task assigned to them has nowhere to go.
    """
    return OnboardingStatus.model_validate(service.status())
