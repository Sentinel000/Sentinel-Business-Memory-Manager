"""Admin and operational endpoints."""

from fastapi import APIRouter

from app.dependencies import DbSession, FounderUser
from app.services.chase_service import run_chase_cycle

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-chase")
def run_chase_now(
    current_founder: FounderUser,
    db: DbSession,
) -> dict[str, int | str]:
    """Run one chase cycle for this tenant immediately.

    Deterministic, not an agent — deciding who has gone quiet is a query. Safe to
    call repeatedly: a task chased within the cadence will not be chased again, so
    this cannot double-remind anyone.
    """
    result = run_chase_cycle(db, current_founder.company)
    db.commit()
    return {
        "status": "completed",
        "company": result.company,
        "reminded": result.reminded,
        "escalated": result.escalated,
    }
