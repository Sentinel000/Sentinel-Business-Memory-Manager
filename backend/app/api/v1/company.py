"""Company and persona configuration."""

from fastapi import APIRouter

from app.dependencies import CompanyId, CompanyRepo, DbSession, FounderUser
from app.exceptions import NotFoundError
from app.models.company import Company
from app.models.task import Task
from app.repositories.task import TERMINAL_STATUSES
from app.schemas.company import CompanyRead, CompanyUpdate

router = APIRouter(prefix="/company", tags=["company"])


def _read(company: Company) -> CompanyRead:
    """Never serialise slack_bot_token — only whether one exists."""
    return CompanyRead(
        id=company.id,
        name=company.name,
        persona_config=company.persona_config or {},
        escalation_after_days=company.escalation_after_days,
        max_chases=company.max_chases,
        auto_approve_threshold=company.auto_approve_threshold,
        slack_connected=bool(company.slack_bot_token),
        slack_team_id=company.slack_team_id,
        knowledge_connected=bool(company.hydra_tenant_id),
    )


@router.get("", response_model=CompanyRead)
def get_company(repo: CompanyRepo, company_id: CompanyId, _: FounderUser) -> CompanyRead:
    company = repo.get(company_id)
    if company is None:
        raise NotFoundError("Company not found.")
    return _read(company)


@router.patch("", response_model=CompanyRead)
def update_company(
    payload: CompanyUpdate,
    repo: CompanyRepo,
    company_id: CompanyId,
    _: FounderUser,
    db: DbSession,
) -> CompanyRead:
    """Rename the company, configure the assistant, set the escalation window."""
    company = repo.get(company_id)
    if company is None:
        raise NotFoundError("Company not found.")

    values = payload.model_dump(exclude_unset=True)
    if "persona_config" in values and values["persona_config"] is not None:
        # Stored as plain JSONB, but it has passed the typed model on the way in —
        # including the length cap on company_context.
        company.persona_config = values.pop("persona_config")
    else:
        values.pop("persona_config", None)

    for key, value in values.items():
        setattr(company, key, value)

    if "max_chases" in values and values["max_chases"] is not None:
        _reconcile_chase_limit(db, company)

    db.commit()
    db.refresh(company)
    return _read(company)


def _reconcile_chase_limit(db: DbSession, company: Company) -> None:
    """Hand back tasks that the new, lower limit has already exhausted.

    ``escalated`` is normally set inside the chase cycle, at the moment a task runs
    out of budget. Lowering the limit exhausts tasks retroactively, and they would
    otherwise match neither the chase query (``chase_count < max_chases`` is now
    false) nor the briefing's decision section (``escalated`` is still false) —
    leaving them stranded in Quiet, never chased and never surfaced, which defeats
    the terminal state the whole ladder depends on.

    Raising the limit is deliberately not reversed: the founder has already been
    told about those tasks, and silently pulling them back off the briefing would
    lose work they were asked to decide on.
    """
    db.query(Task).filter(
        Task.company_id == company.id,
        Task.status.notin_(TERMINAL_STATUSES),
        Task.escalated.is_(False),
        Task.chase_count >= company.max_chases,
    ).update({"escalated": True}, synchronize_session=False)
