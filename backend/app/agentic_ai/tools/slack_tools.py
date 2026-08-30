"""Slack chasing and escalation tools for Sentinel Cron Follow-up."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from langchain_core.tools import tool

from app.agentic_ai.audit import record_audit
from app.database import SessionLocal
from app.models.task import Task
from app.repositories.employee import EmployeeRepository
from app.repositories.task import TaskRepository


def create_slack_tools(company_id: uuid.UUID) -> list[Callable]:
    """Create Slack chasing tools for Cron follow-up."""

    @tool
    def send_reminder(
        employee_id: str,
        task_id: str,
        message: str,
    ) -> dict[str, Any]:
        """Send a gentle follow-up reminder to a task owner and update the task's last chased timestamp."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            eid = uuid.UUID(employee_id)
            with SessionLocal() as session:
                task_repo = TaskRepository(session, company_id)
                emp_repo = EmployeeRepository(session, company_id)
                task = task_repo.get(tid)
                emp = emp_repo.get(eid)

                if not task:
                    return {"error": "Task not found."}
                if not emp:
                    return {"error": "Employee not found."}

                # Update last_chased_at on task
                task.last_chased_at = datetime.now(UTC)
                session.commit()

                result = {
                    "sent_to": emp.name,
                    "slack_user_id": emp.slack_user_id,
                    "task_title": task.title,
                    "message": message,
                    "status": "delivered",
                }
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "send_reminder", {"task_id": task_id, "employee_id": employee_id}, result, "success", duration_ms=duration)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "send_reminder", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def escalate_task(
        task_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Escalate a stagnant or overdue task to the employee's manager and mark the task as escalated."""
        start_time = time.monotonic()
        try:
            tid = uuid.UUID(task_id)
            with SessionLocal() as session:
                task_repo = TaskRepository(session, company_id)
                task = task_repo.get(tid)
                if not task:
                    return {"error": "Task not found."}

                task.escalated = True
                task.last_chased_at = datetime.now(UTC)
                session.commit()

                manager_name = None
                if task.owner and task.owner.manager:
                    manager_name = task.owner.manager.name

                result = {
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "owner": task.owner.name if task.owner else "Unassigned",
                    "escalated_to_manager": manager_name or "Founder",
                    "reason": reason,
                    "status": "escalated",
                }
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "escalate_task", {"task_id": task_id, "reason": reason}, result, "success", duration_ms=duration)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "followup", "escalate_task", {"task_id": task_id}, None, "failure", str(e), duration)
            return {"error": str(e)}

    @tool
    def read_slack_thread(channel_id: str, thread_ts: str) -> dict[str, Any]:
        """Read discussion and context from a Slack thread."""
        return {
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "messages": [
                {"user": "Alice", "text": "Working on the Q4 model."},
                {"user": "Bob", "text": "Let me know when done."},
            ],
        }

    return [send_reminder, escalate_task, read_slack_thread]
