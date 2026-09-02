"""Founder briefing — computed, never generated.

Every figure here comes from SQL. No model is involved, deliberately: a briefing
that miscounts is worse than no briefing, and "what is overdue" is a query, not a
retrieval. Architecture Rule 2, applied to the reporting layer.

Four sections, five items each. The cap is the design, not a limitation — a founder
reads a briefing that fits one screen and stops reading one that does not, and a
report nobody reads is indistinguishable from a report that was never built.

Ordered by what a founder can act on: things waiting on *them* first, things about
to break second, movement third, silence last.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.approval import Approval
from app.models.company import Company
from app.models.employee import Employee
from app.models.enums import ApprovalState, ReportedVia, TaskStatus
from app.models.report import Report
from app.models.status_update import StatusUpdate
from app.models.task import Task
from app.services.chase_service import CHASEABLE_STATUSES, TERMINAL_STATUSES

logger = logging.getLogger(__name__)

#: Items per section. See the module docstring.
SECTION_CAP = 5

#: A deadline this close counts as slipping, not merely upcoming.
SOON = timedelta(hours=48)


@dataclass
class Section:
    key: str
    title: str
    #: Shown when the section is empty. Never blank: "nothing slipped" is a real,
    #: reassuring answer, while an empty box reads as a broken feature.
    empty: str
    items: list[dict[str, Any]]
    #: How many matched in total, so a capped section can say "and 7 more".
    total: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "empty": self.empty,
            "items": self.items,
            "total": self.total,
            "hidden": max(self.total - len(self.items), 0),
        }


def _owner_names(db: Session, tasks: list[Task]) -> dict[Any, str]:
    """Resolve owner ids in one query rather than one per row."""
    ids = {t.owner_employee_id for t in tasks if t.owner_employee_id}
    if not ids:
        return {}
    rows = db.execute(select(Employee.id, Employee.name).where(Employee.id.in_(ids))).all()
    return {row[0]: row[1] for row in rows}


def _item(task: Task, owners: dict[Any, str], now: datetime, **extra: Any) -> dict[str, Any]:
    """One row, carrying enough to act on it and enough to verify it.

    ``source_quote`` travels with every item: Rule 6 says a task cites its source,
    and a briefing that asserts without letting the founder check is the black box
    this product exists to replace.
    """
    overdue_days = None
    if task.deadline is not None and task.deadline < now:
        overdue_days = (now - task.deadline).days

    return {
        "task_id": str(task.id),
        "title": task.title,
        "owner": owners.get(task.owner_employee_id) if task.owner_employee_id else None,
        "status": task.status.value,
        "deadline": task.deadline.date().isoformat() if task.deadline else None,
        "overdue_days": overdue_days,
        "chase_count": task.chase_count,
        "source_quote": task.source_quote,
        "source_ref": task.source_ref,
        **extra,
    }


def _base(company_id: Any):
    """Live tasks for one tenant. Finished work is never in a briefing."""
    return (
        select(Task)
        .where(Task.company_id == company_id)
        .where(Task.status.notin_(TERMINAL_STATUSES))
    )


def _needs_decision(db: Session, company: Company, now: datetime) -> Section:
    """Waiting on the founder: chasing has stopped, or nobody has been asked.

    This is the only section that is an action list. Everything below is context.
    """
    stmt = (
        _base(company.id)
        .where(or_(Task.escalated.is_(True), Task.status == TaskStatus.BLOCKED))
        .order_by(Task.deadline.asc().nullslast(), Task.chase_count.desc())
    )
    tasks = list(db.execute(stmt).scalars().all())
    owners = _owner_names(db, tasks)

    items = []
    for task in tasks[:SECTION_CAP]:
        if task.status is TaskStatus.BLOCKED:
            reason = "Blocked — the owner is stuck and needs you"
        else:
            reason = (
                f"No response after {task.chase_count} "
                f"reminder{'s' if task.chase_count != 1 else ''}"
            )
        items.append(_item(task, owners, now, reason=reason))

    pending = db.execute(
        select(func.count())
        .select_from(Approval)
        .where(Approval.company_id == company.id)
        .where(Approval.state == ApprovalState.PENDING)
    ).scalar_one()

    return Section(
        key="needs_decision",
        title="Needs your decision",
        empty="Nothing is waiting on you.",
        items=items,
        total=len(tasks) + pending,
    )


def _slipping(db: Session, company: Company, now: datetime) -> Section:
    """Overdue, or due inside two days. Excludes anything already handed back."""
    stmt = (
        _base(company.id)
        .where(Task.escalated.is_(False))
        .where(Task.deadline.is_not(None))
        .where(Task.deadline < now + SOON)
        .order_by(Task.deadline.asc())
    )
    tasks = list(db.execute(stmt).scalars().all())
    owners = _owner_names(db, tasks)
    return Section(
        key="slipping",
        title="Slipping",
        empty="Nothing is overdue or due in the next two days.",
        items=[_item(t, owners, now) for t in tasks[:SECTION_CAP]],
        total=len(tasks),
    )


def _moved(db: Session, company: Company, now: datetime, since: datetime) -> Section:
    """What actually changed since the last briefing.

    The delta is the whole reason a report beats a dashboard. Agent-written
    reminders are excluded — our own nudges are not movement.
    """
    stmt = (
        select(StatusUpdate)
        .where(StatusUpdate.company_id == company.id)
        .where(StatusUpdate.created_at >= since)
        .where(StatusUpdate.reported_via != ReportedVia.AGENT)
        .order_by(StatusUpdate.created_at.desc())
    )
    updates = list(db.execute(stmt).scalars().all())

    task_ids = [u.task_id for u in updates]
    tasks = {}
    if task_ids:
        rows = db.execute(_base(company.id).where(Task.id.in_(task_ids))).scalars().all()
        tasks = {t.id: t for t in rows}
    owners = _owner_names(db, list(tasks.values()))

    items = []
    seen = set()
    for update in updates:
        task = tasks.get(update.task_id)
        # One row per task: a task updated three times moved once, as far as a
        # founder scanning a briefing is concerned.
        if task is None or task.id in seen:
            continue
        seen.add(task.id)
        if len(items) >= SECTION_CAP:
            continue
        items.append(
            _item(task, owners, now, moved_to=update.status.value, note=update.note)
        )

    return Section(
        key="moved",
        title="Moved",
        empty="No status changes since the last briefing.",
        items=items,
        total=len(seen),
    )


def _quiet(db: Session, company: Company, now: datetime) -> Section:
    """Chased, still live, and the owner has said nothing back.

    Distinct from "slipping": these may not be late yet. Silence is its own signal,
    and without a push channel it is the main one Sentinel can offer.
    """
    stmt = (
        _base(company.id)
        .where(Task.status.in_(CHASEABLE_STATUSES))
        .where(Task.escalated.is_(False))
        .where(Task.chase_count > 0)
        .order_by(Task.last_chased_at.asc().nullslast())
    )
    tasks = list(db.execute(stmt).scalars().all())
    owners = _owner_names(db, tasks)

    # One query for every owner response, rather than one per task.
    answered: dict[Any, datetime] = {}
    if tasks:
        rows = db.execute(
            select(StatusUpdate.task_id, func.max(StatusUpdate.created_at))
            .where(StatusUpdate.task_id.in_([t.id for t in tasks]))
            .where(StatusUpdate.reported_via != ReportedVia.AGENT)
            .group_by(StatusUpdate.task_id)
        ).all()
        answered = {row[0]: row[1] for row in rows}

    items = []
    for task in tasks[:SECTION_CAP]:
        last = answered.get(task.id) or task.delegated_at or task.created_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        days_silent = (now - last).days if last else None
        items.append(
            _item(
                task, owners, now,
                days_silent=days_silent,
                chases=f"{task.chase_count} of {company.max_chases}",
            )
        )

    return Section(
        key="quiet",
        title="Quiet",
        empty="Everyone has responded.",
        items=items,
        total=len(tasks),
    )


def _counts(db: Session, company: Company, now: datetime) -> dict[str, int]:
    """Headline figures. Computed, so they cannot disagree with the sections."""
    live = list(db.execute(_base(company.id)).scalars().all())
    return {
        "open": len(live),
        "overdue": sum(1 for t in live if t.deadline is not None and t.deadline < now),
        "blocked": sum(1 for t in live if t.status is TaskStatus.BLOCKED),
        "awaiting_you": sum(1 for t in live if t.escalated),
        "unowned": sum(1 for t in live if t.owner_employee_id is None),
        "no_deadline": sum(1 for t in live if t.deadline is None),
    }


def generate_report(db: Session, company: Company, now: datetime | None = None) -> Report:
    """Build today's briefing, replacing it if one already exists.

    Idempotent on ``(company_id, report_date)``: regenerating updates the day's row
    rather than appending. A founder who clicks twice gets one briefing, not two
    versions of the same morning with no way to tell which is current.
    """
    now = now or datetime.now(UTC)
    today: date = now.date()

    existing = db.execute(
        select(Report)
        .where(Report.company_id == company.id)
        .where(Report.report_date == today)
    ).scalar_one_or_none()

    # Movement is measured against the previous briefing, so nothing is reported
    # twice and nothing falls through the gap between runs.
    previous = db.execute(
        select(Report)
        .where(Report.company_id == company.id)
        .where(Report.report_date < today)
        .order_by(Report.report_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    since = (
        datetime.combine(previous.report_date, datetime.min.time(), tzinfo=UTC)
        if previous
        else now - timedelta(days=1)
    )

    sections = [
        _needs_decision(db, company, now),
        _slipping(db, company, now),
        _moved(db, company, now, since),
        _quiet(db, company, now),
    ]
    payload = {"sections": [s.as_dict() for s in sections]}
    counts = _counts(db, company, now)

    report = existing or Report(company_id=company.id, report_date=today)
    report.sections = payload
    report.counts = counts
    report.generated_at = now
    if existing is None:
        db.add(report)

    db.flush()
    logger.info(
        "Report for %s on %s: %s", company.name, today, counts
    )
    return report
