"""Verification: the reports and reminders HTTP surface, including role scoping.

    python -m scripts.verify_reports_api
"""

import sys
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Company, Employee, Task, TaskStatus, User, UserRole
from app.models.report import Report
from app.models.status_update import StatusUpdate

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{f'  — {detail}' if detail else ''}")
    if not condition:
        FAILURES.append(label)


def main() -> int:
    db = SessionLocal()
    client = TestClient(app)
    tag = uuid.uuid4().hex[:8]

    company = Company(name=f"api-verify-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()
    emp = Employee(company_id=company.id, name="Alice", role_title="Eng")
    db.add(emp)
    db.flush()
    founder = User(
        company_id=company.id, email=f"f-{tag}@example.com",
        password_hash=hash_password("x" * 12), role=UserRole.FOUNDER, full_name="F",
    )
    employee_user = User(
        company_id=company.id, email=f"e-{tag}@example.com",
        password_hash=hash_password("x" * 12), role=UserRole.EMPLOYEE,
        full_name="Alice", employee_id=emp.id,
    )
    db.add_all([founder, employee_user])
    task = Task(
        company_id=company.id, title="ship the thing", status=TaskStatus.APPROVED,
        owner_employee_id=emp.id, idempotency_key=f"api-{tag}",
        source_quote="Alice said she'd ship it",
    )
    db.add(task)
    db.commit()

    ftok = create_access_token(user_id=founder.id, company_id=company.id, role=founder.role)
    etok = create_access_token(
        user_id=employee_user.id, company_id=company.id, role=employee_user.role
    )
    fh = {"Authorization": f"Bearer {ftok}"}
    eh = {"Authorization": f"Bearer {etok}"}

    try:
        print("\n1. Reports — founder only")
        check("anonymous is refused", client.get("/api/v1/reports/today").status_code == 401)
        check("employee is refused", client.get("/api/v1/reports/today", headers=eh).status_code == 403)

        r = client.get("/api/v1/reports/today", headers=fh)
        check("no briefing yet returns 200 null", r.status_code == 200 and r.json() is None,
              "not a 404 — never having asked is a normal state")

        print("\n2. Generate")
        r = client.post("/api/v1/reports/generate", headers=fh)
        check("generate succeeds", r.status_code == 200, f"HTTP {r.status_code}")
        body = r.json()
        check("four sections", len(body["sections"]) == 4,
              [s["key"] for s in body["sections"]])
        check("counts present", "open" in body["counts"], body["counts"])
        first_id = body["id"]

        r2 = client.post("/api/v1/reports/generate", headers=fh)
        check("regenerate returns the same row", r2.json()["id"] == first_id,
              "one briefing per day")
        rows = db.query(Report).filter(Report.company_id == company.id).count()
        check("still one row", rows == 1, f"rows={rows}")

        print("\n3. Read back")
        check("today now returns it",
              client.get("/api/v1/reports/today", headers=fh).json()["id"] == first_id)
        check("history lists it", len(client.get("/api/v1/reports", headers=fh).json()) == 1)
        check("fetch by id", client.get(f"/api/v1/reports/{first_id}", headers=fh).status_code == 200)

        print("\n4. Chase then reminders")
        r = client.post("/api/v1/admin/run-chase", headers=fh)
        check("chase endpoint works", r.status_code == 200, r.json())

        # Force the task quiet so a reminder is actually due.
        db.expire_all()
        t = db.get(Task, task.id)
        from datetime import UTC, datetime, timedelta
        t.created_at = datetime.now(UTC) - timedelta(days=10)
        t.delegated_at = t.created_at
        db.commit()

        r = client.post("/api/v1/admin/run-chase", headers=fh)
        check("chase reminds the quiet task", r.json()["reminded"] == 1, r.json())

        rem = client.get("/api/v1/me/reminders", headers=eh)
        check("employee sees the reminder", rem.status_code == 200 and len(rem.json()) == 1,
              f"HTTP {rem.status_code}")
        if rem.json():
            item = rem.json()[0]
            check("reminder names its task", item["task_title"] == "ship the thing")
            check("reminder is unanswered", item["answered"] is False)
            print(f"        note: {item['note']!r}")

        check("founder cannot read employee reminders",
              client.get("/api/v1/me/reminders", headers=fh).status_code == 403)

        print("\n5. Replying clears it")
        r = client.post(
            f"/api/v1/me/tasks/{task.id}/status",
            headers=eh, json={"status": "in_progress", "note": "on it"},
        )
        check("employee can report status", r.status_code == 200, f"HTTP {r.status_code}")
        rem = client.get("/api/v1/me/reminders", headers=eh).json()
        check("reminder now marked answered", rem and rem[0]["answered"] is True)

        print("\n6. Delete")
        check("delete works",
              client.delete(f"/api/v1/reports/{first_id}", headers=fh).status_code == 204)
        check("gone afterwards",
              client.get(f"/api/v1/reports/{first_id}", headers=fh).status_code == 404)

    finally:
        db.rollback()
        for model in (Report, StatusUpdate, Task):
            db.query(model).filter(model.company_id == company.id).delete()
        db.query(User).filter(User.company_id == company.id).delete()
        db.query(Employee).filter(Employee.company_id == company.id).delete()
        db.query(Company).filter(Company.id == company.id).delete()
        db.commit()
        db.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("All API checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
