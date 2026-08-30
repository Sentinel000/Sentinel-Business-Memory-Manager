"""Employee listing tools for Sentinel."""

import time
import uuid
from typing import Any, Callable

from langchain_core.tools import tool

from app.agentic_ai.audit import record_audit
from app.database import SessionLocal
from app.repositories.employee import EmployeeRepository
from app.schemas.employee import EmployeeSummary


def create_employee_tools(company_id: uuid.UUID) -> list[Callable]:
    """Create employee listing tool for Sentinel agents."""

    @tool
    def list_employees(q: str | None = None) -> list[dict[str, Any]]:
        """List employees and team members in the company. Optionally search by name prefix."""
        start_time = time.monotonic()
        try:
            with SessionLocal() as session:
                repo = EmployeeRepository(session, company_id)
                employees = repo.list_all(search=q) if q else repo.list_all()
                result = [
                    EmployeeSummary.from_employee(
                        emp,
                        manager_name=emp.manager.name if emp.manager else None,
                        is_user=emp.user is not None,
                    ).model_dump(mode="json")
                    for emp in employees
                ]
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "list_employees", {"q": q}, {"count": len(result)}, "success", duration_ms=duration)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start_time) * 1000)
            record_audit(None, company_id, "sentinel", "list_employees", {"q": q}, None, "failure", str(e), duration)
            return [{"error": str(e)}]

    return [list_employees]
