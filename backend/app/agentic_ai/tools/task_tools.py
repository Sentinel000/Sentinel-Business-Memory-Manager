"""Task tools with closure-pinned scoping, audit logging, and thread-safe session execution (Rules 1-5)."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.agentic_ai.audit import record_audit
from app.database import SessionLocal
from app.models.enums import ApprovalState, TaskStatus
from app.models.task import Task
from app.repositories.employee import EmployeeRepository
from app.schemas.task import StatusUpdateCreate, TaskCreate, TaskDetail, TaskSummary, TaskUpdate
from app.services.task_service import TaskService


def _task_to_summary(t: Task) -> dict[str, Any]:
    s = TaskSummary.model_validate(t)
    if t.owner:
        s.owner_name = t.owner.name
    return s.model_dump(mode="json")


def _task_to_detail(t: Task) -> dict[str, Any]:
    d = TaskDetail.model_validate(t)
    if t.owner:
        d.owner_name = t.owner.name
    return d.model_dump(mode="json")


def create_founder_task_tools(company_id: uuid.UUID, user_id: uuid.UUID) -> list[Callable]:
    """Create task tools for Founder chat mode."""

    @tool
    def query_tasks(
        status: str | None = None,
        owner_name: str | None = None,
        overdue: bool | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Query and filter tasks across the company. Optionally filter by status (pending_approval, approved, in_progress, blocked, done, rejected), owner name, or overdue status."""
        start_time = time.monotonic()
        try:
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                status_enum = TaskStatus(status) if status else None

                # list_filtered filters by owner id, not name. Resolve it here, and
                # refuse to pick when the name is ambiguous rather than answering
                # about the wrong person.
                owner_id = None
                if owner_name:
                    matches = EmployeeRepository(session, company_id).search_by_name(owner_name)
                    if not matches:
                        return {"error": f"No employee matching {owner_name!r}."}
                    if len(matches) > 1:
                        names = ", ".join(f"{m.name} ({m.role_title or 'no title'})" for m in matches)
                        return {"error": f"{owner_name!r} is ambiguous — matches: {names}. Ask which one."}
                    owner_id = matches[0].id

                tasks = service.tasks.list_filtered(
                    statuses=[status_enum] if status_enum else None,
                    owner_employee_id=owner_id,
                    overdue=overdue,
                    limit=limit,
                )
                items = [_task_to_summary(t) for t in tasks]
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "query_tasks", {"status": status, "owner_name": owner_name, "overdue": overdue}, {"count": len(items)}, "success", duration_ms=duration)
            # `kind` is what the chat UI keys its renderer on. Set here, on the
            # success path only, so it cannot describe a result that did not happen.
            return {"kind": "task_list", "count": len(items), "items": items}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "query_tasks", {"status": status}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def get_task_detail(task_id: str) -> dict[str, Any]:
        """Fetch complete details, description, timeline, and audit history of a specific task."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.get_or_404(tid)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "get_task_detail", {"task_id": task_id}, detail, "success", duration_ms=duration)
            return {"kind": "task_detail", "task": detail}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "get_task_detail", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def create_task(
        title: str,
        description: str | None = None,
        owner_employee_id: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        """Create a new approved task (founder direct creation)."""
        start_time = time.monotonic()
        try:
            owner_uuid = uuid.UUID(owner_employee_id) if owner_employee_id else None
            deadline_dt = datetime.fromisoformat(deadline) if deadline else None
            payload = TaskCreate(
                title=title,
                description=description,
                owner_employee_id=owner_uuid,
                deadline=deadline_dt,
            )
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.create_manual(payload, user_id=user_id)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "create_task", {"title": title, "owner": owner_employee_id}, detail, "success", duration_ms=duration)
            return {"kind": "task_created", "task": detail}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "create_task", {"title": title}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def update_task(
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        owner_employee_id: str | None = None,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        """Update fields of an existing task."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            owner_uuid = uuid.UUID(owner_employee_id) if owner_employee_id else None
            deadline_dt = datetime.fromisoformat(deadline) if deadline else None
            payload = TaskUpdate(
                title=title,
                description=description,
                owner_employee_id=owner_uuid,
                deadline=deadline_dt,
            )
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.patch(tid, payload)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "update_task", {"task_id": task_id}, detail, "success", duration_ms=duration)
            return {"kind": "task_updated", "task": detail}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "update_task", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def approve_task(task_id: str) -> dict[str, Any]:
        """Approve a task currently pending approval."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.approve_pending(tid, decider_user_id=user_id)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "approve_task", {"task_id": task_id}, detail, "success", duration_ms=duration)
            return {"kind": "task_approved", "task": detail}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "approve_task", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def reject_task(task_id: str, reason: str | None = None) -> dict[str, Any]:
        """Reject a task currently pending approval."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.reject_pending(tid, decider_user_id=user_id, reason=reason)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "reject_task", {"task_id": task_id, "reason": reason}, detail, "success", duration_ms=duration)
            return {"kind": "task_rejected", "task": detail}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "reject_task", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    return [query_tasks, get_task_detail, create_task, update_task, approve_task, reject_task]


def create_employee_task_tools(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> list[Callable]:
    """Create task tools for Employee chat mode — closure pinned to employee_id."""

    @tool
    def query_my_tasks(
        status: str | None = None,
        overdue: bool | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List tasks assigned to you. Optionally filter by status (in_progress, blocked, done) or overdue status."""
        start_time = time.monotonic()
        try:
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                status_enum = TaskStatus(status) if status else None
                tasks = service.tasks.list_filtered(
                    statuses=[status_enum] if status_enum else None,
                    owner_employee_id=employee_id,  # Closure pinned: model cannot alter this
                    overdue=overdue,
                    limit=limit,
                )
                result = [_task_to_summary(t) for t in tasks]
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "query_my_tasks", {"status": status, "overdue": overdue}, {"count": len(result)}, "success", duration_ms=duration)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "query_my_tasks", {"status": status}, None, "failure", str(e), duration)
            return [{"error": str(e)}]

    @tool
    def get_my_task_detail(task_id: str) -> dict[str, Any]:
        """Fetch details for one of your assigned tasks. Only returns tasks assigned to you."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.get_owned_or_404(tid, employee_id)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "get_my_task_detail", {"task_id": task_id}, detail, "success", duration_ms=duration)
            return detail
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "get_my_task_detail", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": "Task not found."}

    @tool
    def report_my_status(
        task_id: str,
        status: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Report a status update on one of your assigned tasks (status must be in_progress, blocked, or done)."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            status_enum = TaskStatus(status)
            if status_enum not in (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE):
                return {"error": "Status must be in_progress, blocked, or done."}

            payload = StatusUpdateCreate(
                status=status_enum,
                note=note,
                reported_by_employee_id=employee_id,
            )
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                service.get_owned_or_404(tid, employee_id)
                task = service.record_status(tid, payload)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "report_my_status", {"task_id": task_id, "status": status}, detail, "success", duration_ms=duration)
            return detail
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "report_my_status", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    return [query_my_tasks, get_my_task_detail, report_my_status]


def create_cron_task_tools(company_id: uuid.UUID) -> list[Callable]:
    """Create task query tools for Cron follow-up."""

    @tool
    def query_tasks(
        status: str | None = None,
        overdue: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query open and active tasks across the company."""
        start_time = time.monotonic()
        try:
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                status_enum = TaskStatus(status) if status else None
                tasks = service.tasks.list_filtered(
                    statuses=[status_enum] if status_enum else [TaskStatus.APPROVED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
                    overdue=overdue,
                    limit=limit,
                )
                result = [_task_to_summary(t) for t in tasks]
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "query_tasks", {"status": status, "overdue": overdue}, {"count": len(result)}, "success", duration_ms=duration)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "query_tasks", {"status": status}, None, "failure", str(e), duration)
            return [{"error": str(e)}]

    @tool
    def get_task_detail(task_id: str) -> dict[str, Any]:
        """Fetch details of a task being reviewed by follow-up."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                service = TaskService(session, company_id)
                task = service.get_or_404(tid)
                detail = _task_to_detail(task)
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "get_task_detail", {"task_id": task_id}, detail, "success", duration_ms=duration)
            return detail
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "get_task_detail", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    return [query_tasks, get_task_detail]


def create_extractor_task_tools(
    company_id: uuid.UUID,
    threshold: float,
    source_ref: str | None = None,
) -> list[Callable]:
    """Create task extraction tools with the confidence approval gate.

    source_ref is captured here rather than exposed as a tool argument: the model
    cannot attribute a task to a meeting it did not come from. Rule 6 — every task
    cites its source.
    """

    @tool
    def create_extracted_task(
        title: str,
        description: str | None = None,
        owner_employee_id: str | None = None,
        deadline: str | None = None,
        source_quote: str | None = None,
        confidence: float = 0.8,
    ) -> dict[str, Any]:
        """Record an extracted task from transcript or meeting notes. Status is automatically decided by the confidence threshold."""
        start_time = time.monotonic()
        try:
            # A name here is a model mistake, not an owner. Reject it with instructions
            # rather than guessing which "Mark" was meant — "ask Mark" must never
            # silently pick the wrong one.
            if owner_employee_id:
                try:
                    owner_uuid = uuid.UUID(owner_employee_id)
                except ValueError:
                    return {
                        "error": (
                            f"owner_employee_id must be a UUID, got {owner_employee_id!r}. "
                            "Call list_employees to look up the id, then retry. If you "
                            "cannot identify them confidently, omit owner_employee_id."
                        )
                    }
            else:
                owner_uuid = None
            deadline_dt = datetime.fromisoformat(deadline) if deadline else None

            # Rule 6 is not optional on the agent path. A founder may type a task
            # with no citation; an extractor may not, because the quote is the only
            # thing that makes the extraction checkable.
            if not source_quote or not source_quote.strip():
                return {
                    "error": (
                        "source_quote is required: pass the verbatim sentence from "
                        "the transcript that this task came from."
                    )
                }

            # Rule 3. A deterministic key means re-running extraction over the same
            # meeting returns the existing task instead of duplicating it — which is
            # what create_pending's contract promises and a fresh uuid4 broke.
            idem = f"extract:{source_ref or 'adhoc'}:{title.strip().lower()}"

            auto_approve = threshold < 1.0 and confidence >= threshold

            with SessionLocal() as session:
                service = TaskService(session, company_id)
                # Routed through the service rather than constructing a Task here.
                # A bare Task row leaves the task pending with no `approvals` row,
                # and the approval queue reads from `approvals` — so the task was
                # invisible to the founder it was waiting on.
                task, created = service.create_pending(
                    title=title,
                    idempotency_key=idem,
                    source_quote=source_quote,
                    source_ref=source_ref,
                    description=description,
                    owner_employee_id=owner_uuid,
                    deadline=deadline_dt,
                    confidence=confidence,
                )

                if created and auto_approve:
                    # The founder set a threshold; clearing it *is* their decision,
                    # made in advance. Recorded as a real approval row with no
                    # decider rather than a task that appears pre-blessed.
                    approval = task.approval
                    if approval is not None:
                        approval.state = ApprovalState.APPROVED
                        approval.decided_at = datetime.now(UTC)
                    task.status = TaskStatus.APPROVED

                # create_pending flushes but does not commit. Without this the block
                # exits, the transaction rolls back, and the tool reports success on
                # a task that does not exist.
                session.commit()
                session.refresh(task)
                detail = _task_to_detail(task)

            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "extractor", "create_extracted_task", {"title": title, "confidence": confidence, "status": detail.get("status"), "duplicate": not created}, detail, "success", duration_ms=duration)
            return {"kind": "task_created", "task": detail, "duplicate": not created}
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "extractor", "create_extracted_task", {"title": title}, None, "failure", str(e), duration)
            return {"error": str(e)}

    return [create_extracted_task]
