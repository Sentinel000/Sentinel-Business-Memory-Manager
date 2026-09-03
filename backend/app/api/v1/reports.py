"""Founder briefings — generated on demand, never on a schedule.

On demand because the founder reads this when they sit down. A briefing built at
08:00 is stale by the time anyone opens it, and there is no way to refresh one that
also re-chases the team — which is exactly why chasing and reporting are separate
paths rather than one agent doing both.
"""

import uuid
from datetime import date

from fastapi import APIRouter, status

from app.dependencies import CompanyId, CompanyRepo, DbSession, FounderUser
from app.exceptions import NotFoundError
from app.models.report import Report
from app.schemas.report import ReportRead, ReportSummary
from app.services.report_service import generate_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _read(report: Report) -> ReportRead:
    payload = report.sections or {}
    return ReportRead(
        id=report.id,
        report_date=report.report_date,
        generated_at=report.generated_at,
        counts=report.counts or {},
        sections=payload.get("sections", []),
    )


@router.get("", response_model=list[ReportSummary])
def list_reports(
    db: DbSession,
    company_id: CompanyId,
    _: FounderUser,
    limit: int = 30,
) -> list[ReportSummary]:
    """Past briefings, newest first."""
    rows = (
        db.query(Report)
        .filter(Report.company_id == company_id)
        .order_by(Report.report_date.desc())
        .limit(limit)
        .all()
    )
    return [ReportSummary.model_validate(r) for r in rows]


@router.post("/generate", response_model=ReportRead, status_code=status.HTTP_200_OK)
def generate(
    db: DbSession,
    repo: CompanyRepo,
    company_id: CompanyId,
    _: FounderUser,
) -> ReportRead:
    """Build today's briefing, replacing today's if one exists.

    Returns 200 rather than 201 because regenerating is the common case and it is
    the same resource either way — one briefing per day, updated in place.
    """
    company = repo.get(company_id)
    if company is None:
        raise NotFoundError("Company not found.")

    report = generate_report(db, company)
    db.commit()
    db.refresh(report)
    return _read(report)


@router.get("/today", response_model=ReportRead | None)
def get_today(
    db: DbSession,
    company_id: CompanyId,
    _: FounderUser,
) -> ReportRead | None:
    """Today's briefing, or null if it has not been generated yet.

    Null rather than 404: not having asked for today's briefing is a normal state
    the page renders as a prompt, not an error.
    """
    report = (
        db.query(Report)
        .filter(Report.company_id == company_id, Report.report_date == date.today())
        .one_or_none()
    )
    return _read(report) if report else None


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: uuid.UUID,
    db: DbSession,
    company_id: CompanyId,
    _: FounderUser,
) -> ReportRead:
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.company_id == company_id)
        .one_or_none()
    )
    if report is None:
        raise NotFoundError("Report not found.")
    return _read(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: uuid.UUID,
    db: DbSession,
    company_id: CompanyId,
    _: FounderUser,
) -> None:
    """Discard a briefing. It can always be rebuilt — nothing here is a source of
    truth, it is a view over tasks that still exist."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.company_id == company_id)
        .one_or_none()
    )
    if report is None:
        raise NotFoundError("Report not found.")
    db.delete(report)
    db.commit()
