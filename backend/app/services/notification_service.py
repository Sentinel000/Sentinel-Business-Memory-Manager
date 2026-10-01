"""What Sentinel says by email, and to whom.

Three messages, one per moment in the loop where a person needs to know something:

- **delegated** - a commitment just became yours (the founder approved it, typed
  it, or reassigned it to you).
- **reminded** - the chase cycle nudged you. Same ladder as the in-app reminder.
- **blocked** - an owner flagged a blocker; every founder hears about it at once,
  because a blocker is waiting on *them*.

The owner's emails carry one-tap status links (see ``core/action_tokens``), so
answering a reminder never needs a login. That is the whole point: an in-app nudge
that nobody opens is indistinguishable from silence.

Every function here is best-effort. A notification failure is logged and swallowed,
never raised into the approval, chase or status update that triggered it - those
have already been committed and are the source of truth.

All task text is HTML-escaped. Titles and quotes come from transcripts and pasted
threads, which is text anyone can write.
"""

import logging
import threading
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.action_tokens import issue_action_token
from app.models.approval import Approval
from app.models.company import Company
from app.models.employee import Employee
from app.models.enums import TaskStatus, UserRole
from app.models.task import Task
from app.models.user import User
from app.services.email_service import OutgoingEmail, dispatch

logger = logging.getLogger(__name__)

#: A task in one of these has an owner who is expected to act.
ACTIVE_STATUSES = (TaskStatus.APPROVED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)

# The same three tints the employee task view uses, so the email and the app agree.
_BUTTONS = (
    ("done", "Complete", "#047857", "#ecfdf5", "#a7f3d0"),
    ("in_progress", "In progress", "#b45309", "#fffbeb", "#fde68a"),
    ("blocked", "Blocked", "#be123c", "#fff1f2", "#fecdd3"),
)

_INK = "#0c0a09"
_WARM = "#78716c"
_ASH = "#a8a29e"
_BORDER = "#e8e6e5"
_CANVAS = "#fafaf9"
_CYAN = "#3398e1"
_WASH = "#e8f4fd"
_META_SEP = "  ·  "
_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,Arial,sans-serif"


# --- recipients ----------------------------------------------------------------


def _employee_address(employee: Employee | None) -> str | None:
    """The employee's own address, falling back to their login's."""
    if employee is None:
        return None
    if employee.email:
        return employee.email
    if employee.user is not None and employee.user.email:
        return employee.user.email
    return None


def _founders(db: Session, company_id: uuid.UUID) -> list[User]:
    stmt = (
        select(User)
        .where(User.company_id == company_id)
        .where(User.role == UserRole.FOUNDER)
        .where(User.is_active.is_(True))
    )
    return list(db.execute(stmt).scalars().all())


def _asker(db: Session, task: Task, company: Company) -> str:
    """Who the owner should picture asking: the founder who approved it."""
    approval = task.approval
    if approval is not None and approval.decided_by_user_id is not None:
        user = db.get(User, approval.decided_by_user_id)
        if user is not None and user.full_name:
            return user.full_name
    for founder in _founders(db, company.id):
        if founder.full_name:
            return founder.full_name
    return company.name


def _load_tasks(db: Session, company_id: uuid.UUID, task_ids: Iterable[uuid.UUID]) -> list[Task]:
    ids = list(dict.fromkeys(task_ids))
    if not ids:
        return []
    stmt = (
        select(Task)
        .where(Task.company_id == company_id)
        .where(Task.id.in_(ids))
        .options(
            selectinload(Task.owner).selectinload(Employee.user),
            selectinload(Task.approval),
        )
    )
    return list(db.execute(stmt).scalars().all())


# --- wording -------------------------------------------------------------------


def _due_phrase(deadline: datetime | None, now: datetime) -> str | None:
    if deadline is None:
        return None
    due = deadline if deadline.tzinfo else deadline.replace(tzinfo=UTC)
    days = (due.date() - now.date()).days
    if days < 0:
        late = -days
        return f"Was due {late} day{'s' if late != 1 else ''} ago"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    return f"Due {due:%a} {due.day} {due:%b}"


def _source_line(source_ref: str | None) -> str | None:
    if not source_ref:
        return None
    if source_ref.startswith("Meeting:"):
        return f"From the meeting “{source_ref.split(':', 1)[1].strip()}”"
    return f"From {source_ref}"


def _links(task: Task, employee_id: uuid.UUID) -> dict[str, str]:
    token = issue_action_token(
        task_id=task.id, employee_id=employee_id, company_id=task.company_id
    )
    base = settings.app_base_url.rstrip("/")
    return {status: f"{base}/act/{token}?s={status}" for status, *_ in _BUTTONS}


def _base() -> str:
    return settings.app_base_url.rstrip("/")


# --- rendering -----------------------------------------------------------------


def _layout(*, preheader: str, kicker: str, heading: str, body: str, footer: str) -> str:
    """One table-based shell. Email clients ignore most CSS, so styles are inline."""
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:{_CANVAS};">
<span style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_CANVAS};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
<tr><td style="padding:0 4px 14px;font-family:{_FONT};font-size:13px;font-weight:600;color:{_INK};letter-spacing:-0.01em;">
<span style="display:inline-block;width:20px;height:20px;line-height:20px;border-radius:6px;background:{_INK};color:#3ba6f1;text-align:center;font-size:12px;font-weight:700;margin-right:8px;">S</span>Sentinel</td></tr>
<tr><td style="background:#ffffff;border:1px solid {_BORDER};border-radius:12px;padding:24px 20px 20px;word-break:break-word;">
<div style="font-family:{_FONT};font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:{_ASH};margin:0 0 10px;">{escape(kicker)}</div>
<div style="font-family:{_FONT};font-size:22px;line-height:1.3;font-weight:500;color:{_INK};letter-spacing:-0.02em;margin:0 0 16px;">{escape(heading)}</div>
{body}
</td></tr>
<tr><td style="padding:16px 6px 0;font-family:{_FONT};font-size:12px;line-height:1.6;color:{_ASH};">{footer}</td></tr>
</table></td></tr></table></body></html>"""


def _para(text: str, *, color: str = _WARM, size: int = 15) -> str:
    return (
        f'<p style="font-family:{_FONT};font-size:{size}px;line-height:1.6;color:{color};'
        f'margin:0 0 14px;">{text}</p>'
    )


def _task_block(task: Task, now: datetime) -> str:
    meta = [p for p in (_due_phrase(task.deadline, now), _source_line(task.source_ref)) if p]
    # Joined outside the f-string: a backslash escape inside an f-string expression
    # is a syntax error before Python 3.12.
    meta_text = _META_SEP.join(meta)
    meta_html = (
        f'<div style="font-family:{_FONT};font-size:13px;color:{_WARM};margin-top:6px;">'
        f'{escape(meta_text)}</div>'
        if meta else ""
    )
    quote_html = ""
    if task.source_quote:
        quote_html = (
            f'<div style="margin-top:12px;border-left:3px solid {_CYAN};background:{_WASH};'
            f'padding:10px 12px;border-radius:0 6px 6px 0;font-family:{_FONT};font-size:14px;'
            f'line-height:1.5;color:{_INK};">“{escape(task.source_quote)}”</div>'
        )
    return (
        f'<div style="border:1px solid {_BORDER};border-radius:10px;padding:16px;margin:0 0 20px;">'
        f'<div style="font-family:{_FONT};font-size:16px;font-weight:600;color:{_INK};">'
        f"{escape(task.title)}</div>{meta_html}{quote_html}</div>"
    )


def _buttons(links: dict[str, str]) -> str:
    # Inline-blocks rather than one table row: three buttons in a row need ~420px,
    # wider than a phone, and a table that cannot shrink drags the whole email wider
    # than the screen. Inline-blocks wrap to a second line instead.
    buttons = "".join(
        f'<a href="{escape(links[status])}" '
        f'style="display:inline-block;margin:0 6px 8px 0;font-family:{_FONT};font-size:14px;'
        f"font-weight:600;color:{fg};background:{bg};border:1px solid {line};"
        f'border-radius:999px;padding:9px 16px;text-decoration:none;">{label}</a>'
        for status, label, fg, bg, line in _BUTTONS
    )
    return _para("Update it in one tap. No login needed.", size=13, color=_ASH) + f"<div>{buttons}</div>"



def _primary_button(href: str, label: str) -> str:
    return (
        f'<a href="{escape(href)}" style="display:inline-block;font-family:{_FONT};font-size:14px;'
        f"font-weight:600;color:#ffffff;background:#3ba6f1;border:1px solid {_CYAN};"
        f'border-radius:999px;padding:10px 20px;text-decoration:none;">{escape(label)}</a>'
    )


def _owner_footer(company: Company) -> str:
    return (
        f"You are getting this because {escape(company.name)} uses Sentinel to keep track "
        f'of who owes what. <a href="{escape(_base())}/me" style="color:{_WARM};">'
        f"See everything assigned to you</a>."
    )


def _text_task(task: Task, now: datetime) -> str:
    lines = [task.title]
    lines += [p for p in (_due_phrase(task.deadline, now), _source_line(task.source_ref)) if p]
    if task.source_quote:
        lines.append(f'"{task.source_quote}"')
    return "\n".join(lines)


def _text_links(links: dict[str, str]) -> str:
    return "\n".join(f"{label}: {links[status]}" for status, label, *_ in _BUTTONS)


# --- messages ------------------------------------------------------------------


def build_delegation_email(db: Session, task: Task, company: Company) -> OutgoingEmail | None:
    owner = task.owner
    to = _employee_address(owner)
    if owner is None or to is None or task.status not in ACTIVE_STATUSES:
        return None

    now = datetime.now(UTC)
    asker = _asker(db, task, company)
    links = _links(task, owner.id)
    first = owner.name.split()[0] if owner.name else "there"

    html = _layout(
        preheader=f"{asker} asked you to take this on.",
        kicker="New commitment",
        heading=f"Hi {first}, this one is yours",
        body=_para(f"{escape(asker)} asked you to take this on.")
        + _task_block(task, now)
        + _buttons(links),
        footer=_owner_footer(company),
    )
    text = (
        f"Hi {first},\n\n{asker} asked you to take this on.\n\n{_text_task(task, now)}\n\n"
        f"Update it in one tap, no login needed:\n{_text_links(links)}\n\n"
        f"Everything assigned to you: {_base()}/me\n"
    )
    return OutgoingEmail(to=to, subject=f"New commitment: {task.title}", text=text, html=html)


def build_reminder_email(db: Session, task: Task, company: Company) -> OutgoingEmail | None:
    owner = task.owner
    to = _employee_address(owner)
    if owner is None or to is None:
        return None

    now = datetime.now(UTC)
    asker = _asker(db, task, company)
    links = _links(task, owner.id)
    n, budget = task.chase_count, company.max_chases

    if task.deadline is not None and _due_phrase(task.deadline, now).startswith("Was due"):
        lead = f"{_due_phrase(task.deadline, now)} and there has been no update yet."
    elif task.deadline is not None:
        lead = f"{_due_phrase(task.deadline, now)}. Is it on track?"
    else:
        lead = "This has no deadline and has gone quiet. Is it still live?"

    last = (
        f" This is the last reminder. Without an update it goes back to {asker} to decide."
        if n >= budget else ""
    )

    html = _layout(
        preheader=lead,
        kicker=f"Reminder {n} of {budget}",
        heading="A quick check-in",
        body=_para(escape(lead + last)) + _task_block(task, now) + _buttons(links),
        footer=_owner_footer(company),
    )
    text = (
        f"Reminder {n} of {budget}\n\n{lead}{last}\n\n{_text_task(task, now)}\n\n"
        f"Update it in one tap, no login needed:\n{_text_links(links)}\n"
    )
    return OutgoingEmail(
        to=to, subject=f"Reminder {n} of {budget}: {task.title}", text=text, html=html
    )


def build_blocker_emails(
    db: Session, task: Task, company: Company, *, reported_by: Employee, note: str | None
) -> list[OutgoingEmail]:
    now = datetime.now(UTC)
    who = reported_by.name
    note_html = (
        f'<div style="margin:0 0 18px;border-left:3px solid #be123c;background:#fff1f2;'
        f'padding:10px 12px;border-radius:0 6px 6px 0;font-family:{_FONT};font-size:14px;'
        f'line-height:1.5;color:{_INK};">{escape(note)}</div>'
        if note else _para("No note was added.", size=14, color=_ASH)
    )
    html = _layout(
        preheader=f"{who} is blocked and needs you.",
        kicker="Blocker",
        heading=f"{who} is blocked",
        body=_para(f"{escape(who)} flagged a blocker. It is waiting on you now, and Sentinel "
                   "will not chase them about it.")
        + note_html
        + _task_block(task, now)
        + _primary_button(f"{_base()}/tasks", "Open in Sentinel"),
        footer=f"Sent to the founders of {escape(company.name)}.",
    )
    text = (
        f"{who} flagged a blocker. It is waiting on you now.\n\n"
        f"Their note: {note or '(none)'}\n\n{_text_task(task, now)}\n\nOpen Sentinel: {_base()}/tasks\n"
    )
    return [
        OutgoingEmail(to=f.email, subject=f"Blocked: {task.title}", text=text, html=html)
        for f in _founders(db, company.id)
        if f.email
    ]


# --- entry points --------------------------------------------------------------


def task_ids_for_approvals(
    db: Session, company_id: uuid.UUID, approval_ids: Iterable[uuid.UUID]
) -> list[uuid.UUID]:
    ids = list(approval_ids)
    if not ids:
        return []
    stmt = (
        select(Approval.task_id)
        .where(Approval.company_id == company_id)
        .where(Approval.id.in_(ids))
    )
    return list(db.execute(stmt).scalars().all())


def notify_delegated(
    db: Session, company_id: uuid.UUID, task_ids: Iterable[uuid.UUID]
) -> threading.Thread | None:
    """Tell each owner a commitment just became theirs. Call after commit."""
    if not settings.email_enabled:
        return None
    try:
        company = db.get(Company, company_id)
        if company is None:
            return None
        emails = [
            e for task in _load_tasks(db, company_id, task_ids)
            if (e := build_delegation_email(db, task, company)) is not None
        ]
        return dispatch(emails)
    except Exception:
        logger.exception("Could not send delegation emails")
        return None


def notify_reminded(
    db: Session, company_id: uuid.UUID, task_ids: Iterable[uuid.UUID]
) -> threading.Thread | None:
    """Email the reminders a chase cycle just wrote. Call after commit."""
    if not settings.email_enabled:
        return None
    try:
        company = db.get(Company, company_id)
        if company is None:
            return None
        emails = [
            e for task in _load_tasks(db, company_id, task_ids)
            if (e := build_reminder_email(db, task, company)) is not None
        ]
        return dispatch(emails)
    except Exception:
        logger.exception("Could not send reminder emails")
        return None


def notify_blocked(
    db: Session,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    reported_by_employee_id: uuid.UUID,
    note: str | None,
) -> threading.Thread | None:
    """Tell every founder that a blocker is now waiting on them. Call after commit."""
    if not settings.email_enabled:
        return None
    try:
        company = db.get(Company, company_id)
        employee = db.get(Employee, reported_by_employee_id)
        tasks = _load_tasks(db, company_id, [task_id])
        if company is None or employee is None or not tasks:
            return None
        return dispatch(build_blocker_emails(db, tasks[0], company, reported_by=employee, note=note))
    except Exception:
        logger.exception("Could not send blocker emails")
        return None
