"""One-tap status links from email - the only unauthenticated write in the API.

The token *is* the authorisation: it is signed, bound to one task and one employee,
and expires (see ``core/action_tokens``). It is checked again against the database
on every use, so a link stops working the moment the task is reassigned.

GET never changes anything. Mail security scanners - Outlook Safe Links, Gmail's
link checks - fetch every URL in a message before a person sees it. If GET applied
the status, a robot would mark tasks done. GET previews; only the landing page's
POST, which a person has to press, records the update.
"""

from fastapi import APIRouter

from app.core.action_tokens import ActionTokenExpired, ActionClaims, verify_action_token
from app.dependencies import DbSession
from app.exceptions import ConflictError, NotFoundError, SentinelError
from app.models.company import Company
from app.models.employee import Employee
from app.models.enums import ReportedVia, TaskStatus
from app.models.task import Task
from app.schemas.action import ActionApply, ActionPreview, ActionResult
from app.schemas.task import StatusUpdateCreate
from app.services.notification_service import notify_blocked
from app.services.task_service import TaskService

router = APIRouter(prefix="/actions", tags=["actions"])

CLOSED = (TaskStatus.DONE, TaskStatus.REJECTED)


class LinkExpiredError(SentinelError):
    status_code = 410
    code = "LINK_EXPIRED"


def _claims(token: str) -> ActionClaims:
    try:
        claims = verify_action_token(token)
    except ActionTokenExpired:
        raise LinkExpiredError(
            "This link has expired. Open Sentinel to update the task."
        ) from None
    if claims is None:
        # Forged and unknown read the same, so a probe learns nothing.
        raise NotFoundError("This link is not valid.")
    return claims


def _resolve(db, claims: ActionClaims) -> tuple[Task, Employee, Company]:
    tasks = TaskService(db, claims.company_id)
    try:
        task = tasks.get_or_404(claims.task_id)
    except NotFoundError:
        raise NotFoundError("This task no longer exists.") from None

    employee = db.get(Employee, claims.employee_id)
    company = db.get(Company, claims.company_id)
    if employee is None or company is None or employee.company_id != company.id:
        raise NotFoundError("This link is not valid.")

    # Checked on every use, not just at issue: a reassigned task must stop
    # accepting answers from the person it was taken away from.
    if task.owner_employee_id != employee.id:
        raise ConflictError(
            "This task has been reassigned, so this link no longer applies.",
            details={"reason": "reassigned"},
        )
    return task, employee, company


@router.get("/{token}", response_model=ActionPreview)
def preview_action(token: str, db: DbSession) -> ActionPreview:
    """What the link points at. Read-only - see the module docstring."""
    task, employee, company = _resolve(db, _claims(token))
    return ActionPreview(
        task_id=task.id,
        title=task.title,
        status=task.status,
        deadline=task.deadline,
        source_quote=task.source_quote,
        source_ref=task.source_ref,
        owner_name=employee.name,
        company_name=company.name,
        closed=task.status in CLOSED,
    )


@router.post("/{token}", response_model=ActionResult)
def apply_action(token: str, payload: ActionApply, db: DbSession) -> ActionResult:
    """Record the employee's answer, exactly as if they had tapped it in the app."""
    claims = _claims(token)
    task, employee, _ = _resolve(db, claims)

    # A double tap is a success, not an error, and must not add a second timeline
    # entry - the founder would read it as two separate updates.
    if task.status == payload.status:
        return ActionResult(task_id=task.id, title=task.title, status=task.status, changed=False)

    if task.status in CLOSED:
        raise ConflictError(
            f"This task is already {task.status.value.replace('_', ' ')}.",
            details={"reason": "closed", "status": task.status.value},
        )
    if task.status is TaskStatus.PENDING_APPROVAL:
        raise ConflictError(
            "This task is waiting for approval and cannot be updated yet.",
            details={"reason": "pending"},
        )

    # The same path as the in-app buttons, so escalation and the chase counter
    # behave identically whichever surface the answer came from.
    updated = TaskService(db, claims.company_id).record_status(
        task.id,
        StatusUpdateCreate(
            status=payload.status,
            note=payload.note,
            reported_by_employee_id=employee.id,
            reported_via=ReportedVia.EMAIL,
        ),
    )
    db.commit()

    if payload.status is TaskStatus.BLOCKED:
        notify_blocked(
            db, claims.company_id, updated.id,
            reported_by_employee_id=employee.id, note=payload.note,
        )

    return ActionResult(
        task_id=updated.id, title=updated.title, status=updated.status, changed=True
    )
