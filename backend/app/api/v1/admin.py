"""Admin and operational endpoints."""

from fastapi import APIRouter

from app.agentic_ai.agents.followup import run_cron_followup
from app.dependencies import DbSession, FounderUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-followup")
def run_followup_now(
    current_founder: FounderUser,
    db: DbSession,
):
    """Trigger the daily follow-up routine on demand for the current tenant."""
    result = run_cron_followup(db=db, company=current_founder.company)
    return result
