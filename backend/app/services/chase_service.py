"""Chasing — reminding owners of commitments that have gone quiet.

Replaces the Slack DM ladder. Reminders now land in the employee's own dashboard,
which means there is no push: an unread reminder is indistinguishable from an
employee who has not logged in. So the promise changes. Sentinel cannot make someone
respond; it can guarantee the founder knows who has not.

That is why the ladder is short and terminates. Every extra chase postpones the
moment the founder learns a commitment is dead, and an unbounded ladder fills the
briefing with tasks nobody will ever action — which is how a daily report stops
being read.

No agent, no model. Deciding who is overdue is a query, and Architecture Rule 2
applies: ``WHERE status='overdue'`` must never be a fuzzy retrieval.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.enums import ReportedVia, TaskStatus
from app.models.status_update import StatusUpdate
from app.models.task import Task

logger = logging.getLogger(__name__)

#: A task in one of these is finished. Never chased, never counted as quiet.
TERMINAL_STATUSES = (TaskStatus.DONE, TaskStatus.REJECTED)

#: Only these can be chased.
#:
#: BLOCKED is excluded on purpose: the owner has already answered, and the answer
#: was "I am stuck". Nudging someone who told you they are stuck is exactly the
#: noise that trains people to ignore the tool — a blocker goes to the founder
#: instead, immediately, via ``escalated``.
#:
#: PENDING_APPROVAL is excluded because nobody has been asked yet, and
#: ``TaskStatus.OVERDUE`` is absent because nothing in the codebase ever writes it:
#: overdue is derived from ``deadline < now()`` so it can never go stale.
CHASEABLE_STATUSES = (TaskStatus.APPROVED, TaskStatus.IN_PROGRESS)


@dataclass
class ChaseResult:
    company: str
    reminded: int
    escalated: int


def _last_touch():
    """Last time anything happened to a task: a chase, a delegation, or its creation.

    Deliberately not ``updated_at`` — a founder editing a title would otherwise
    silently reset every owner's silence clock.
    """
    return func.coalesce(Task.last_chased_at, Task.delegated_at, Task.created_at)


def _cadence(company: Company) -> timedelta:
    """Silence tolerated before a nudge.

    Reuses ``escalation_after_days`` rather than introducing a second interval that
    would then have to be kept in agreement with it.
    """
    return timedelta(days=max(company.escalation_after_days or 3, 1))


def due_for_chase(db: Session, company: Company, now: datetime | None = None) -> list[Task]:
    """Tasks whose owner should be reminded right now.

    Two clocks, one clause. Silence is the universal trigger — a task with no
    deadline is still a commitment, and undated tasks are precisely the ones that
    rot unnoticed. A deadline does not create the obligation to chase, it only
    brings it forward.
    """
    now = now or datetime.now(UTC)
    quiet_since = now - _cadence(company)

    stmt = (
        select(Task)
        .where(Task.company_id == company.id)
        .where(Task.status.in_(CHASEABLE_STATUSES))
        .where(Task.owner_employee_id.is_not(None))
        .where(Task.escalated.is_(False))
        .where(Task.chase_count < company.max_chases)
        # Eligible: either the deadline has passed, or the owner has been silent
        # for a full cadence. A deadline does not create the obligation to chase,
        # it only brings it forward.
        .where(
            or_(
                Task.deadline.is_not(None) & (Task.deadline < now),
                # delegated_at starts the clock; created_at covers tasks that
                # predate delegation.
                _last_touch() < quiet_since,
            )
        )
        # Rate limit, applied to both paths. Without it an overdue task matches on
        # every single run and burns its entire budget in one afternoon — the
        # deadline stays passed, so the first clause never stops being true.
        .where(
            or_(
                Task.last_chased_at.is_(None),
                Task.last_chased_at < quiet_since,
            )
        )
    )
    return list(db.execute(stmt).scalars().all())


def run_chase_cycle(
    db: Session, company: Company, now: datetime | None = None
) -> ChaseResult:
    """Send one round of reminders for a company, and hand back what is exhausted.

    Idempotent within a cadence window (Rule 3): a task chased a minute ago has a
    fresh ``last_chased_at`` and stops matching, so a double-run cannot double-remind.
    """
    now = now or datetime.now(UTC)
    reminded = 0
    escalated = 0

    for task in due_for_chase(db, company, now):
        task.chase_count += 1
        task.last_chased_at = now

        # The reminder is a timeline entry, so the employee sees it in the same
        # place as their own updates and the founder can audit what was sent.
        # Status is carried unchanged — a reminder is not a status change.
        db.add(
            StatusUpdate(
                company_id=company.id,
                task_id=task.id,
                status=task.status,
                note=_reminder_note(task, company, now),
                reported_by_employee_id=None,
                reported_via=ReportedVia.AGENT,
                idempotency_key=f"chase:{task.id}:{task.chase_count}",
            )
        )
        reminded += 1

        # Budget spent. Stop chasing and put it in front of the founder, who is the
        # only escalation path now that managers cannot be DM'd.
        if task.chase_count >= company.max_chases:
            task.escalated = True
            escalated += 1

    db.flush()
    logger.info(
        "Chase cycle for %s: %d reminded, %d escalated", company.name, reminded, escalated
    )
    return ChaseResult(company=company.name, reminded=reminded, escalated=escalated)


def _reminder_note(task: Task, company: Company, now: datetime) -> str:
    """What the employee reads. Plain and specific, never guilt-tripping."""
    ordinal = f"Reminder {task.chase_count} of {company.max_chases}"
    if task.deadline is not None and task.deadline < now:
        days = (now - task.deadline).days
        return f"{ordinal} — this was due {days} day{'s' if days != 1 else ''} ago."
    if task.deadline is not None:
        return f"{ordinal} — due {task.deadline.date().isoformat()}."
    return f"{ordinal} — no deadline set; is this still live?"


def last_owner_response(db: Session, task_id: uuid.UUID) -> datetime | None:
    """When the owner last said anything, or None if they never have.

    Agent-written reminders are excluded: the question is whether the *person*
    answered, and counting our own nudges as activity would mask exactly the
    silence this is meant to detect.
    """
    stmt = (
        select(StatusUpdate.created_at)
        .where(StatusUpdate.task_id == task_id)
        .where(StatusUpdate.reported_via != ReportedVia.AGENT)
        .order_by(StatusUpdate.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
