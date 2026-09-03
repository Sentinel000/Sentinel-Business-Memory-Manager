"""Verification: the founder's follow-up settings actually persist and take effect.

    python -m scripts.verify_settings
"""

import sys
import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Company, Employee, Task, TaskStatus, User, UserRole
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

    company = Company(name=f"settings-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()
    emp = Employee(company_id=company.id, name="Alice")
    db.add(emp)
    db.flush()
    founder = User(
        company_id=company.id, email=f"s-{tag}@example.com",
        password_hash=hash_password("x" * 12), role=UserRole.FOUNDER, full_name="F",
    )
    db.add(founder)
    db.commit()

    tok = create_access_token(user_id=founder.id, company_id=company.id, role=founder.role)
    h = {"Authorization": f"Bearer {tok}"}

    try:
        print("\n1. Settings are readable")
        body = client.get("/api/v1/company", headers=h).json()
        check("max_chases exposed", body.get("max_chases") == 2, body.get("max_chases"))
        check("cadence exposed", body.get("escalation_after_days") == 3)
        check("threshold exposed", body.get("auto_approve_threshold") == 1.0,
              body.get("auto_approve_threshold"))

        print("\n2. Settings actually persist (they were silently dropped before)")
        r = client.patch("/api/v1/company", headers=h, json={
            "escalation_after_days": 5,
            "max_chases": 3,
            "auto_approve_threshold": 0.8,
        })
        check("patch accepted", r.status_code == 200, f"HTTP {r.status_code}")
        body = r.json()
        check("cadence saved", body["escalation_after_days"] == 5, body["escalation_after_days"])
        check("max_chases saved", body["max_chases"] == 3, body["max_chases"])
        check("threshold saved", body["auto_approve_threshold"] == 0.8,
              body["auto_approve_threshold"])

        db.expire_all()
        fresh = db.get(Company, company.id)
        check("persisted to the database", fresh.max_chases == 3 and fresh.escalation_after_days == 5)

        print("\n3. Bounds are enforced")
        check("max_chases above 5 rejected",
              client.patch("/api/v1/company", headers=h, json={"max_chases": 9}).status_code == 400)
        check("max_chases below 1 rejected",
              client.patch("/api/v1/company", headers=h, json={"max_chases": 0}).status_code == 400)
        check("threshold below 0.5 rejected",
              client.patch("/api/v1/company", headers=h,
                           json={"auto_approve_threshold": 0.1}).status_code == 400)
        check("cadence above 30 rejected",
              client.patch("/api/v1/company", headers=h,
                           json={"escalation_after_days": 60}).status_code == 400)

        print("\n4. Lowering the limit hands back already-exhausted tasks")
        # Two chases spent, under a limit of 3 — not yet escalated.
        task = Task(
            company_id=company.id, title="two chases in", status=TaskStatus.APPROVED,
            owner_employee_id=emp.id, idempotency_key=f"set-{tag}",
            chase_count=2, escalated=False,
        )
        db.add(task)
        db.commit()

        client.patch("/api/v1/company", headers=h, json={"max_chases": 2})
        db.expire_all()
        t = db.get(Task, task.id)
        check("exhausted task is escalated on save", t.escalated is True,
              "otherwise it is stranded: never chased, never surfaced")

        print("\n5. Raising the limit does not silently un-escalate")
        client.patch("/api/v1/company", headers=h, json={"max_chases": 4})
        db.expire_all()
        t = db.get(Task, task.id)
        check("still escalated", t.escalated is True,
              "the founder was already asked to decide")

        print("\n6. Employees cannot change settings")
        emp_user = User(
            company_id=company.id, email=f"e-{tag}@example.com",
            password_hash=hash_password("x" * 12), role=UserRole.EMPLOYEE,
            full_name="Alice", employee_id=emp.id,
        )
        db.add(emp_user)
        db.commit()
        etok = create_access_token(
            user_id=emp_user.id, company_id=company.id, role=emp_user.role
        )
        check("employee patch refused", client.patch(
            "/api/v1/company", headers={"Authorization": f"Bearer {etok}"},
            json={"max_chases": 5},
        ).status_code == 403)

    finally:
        db.rollback()
        db.query(StatusUpdate).filter(StatusUpdate.company_id == company.id).delete()
        db.query(Task).filter(Task.company_id == company.id).delete()
        db.query(User).filter(User.company_id == company.id).delete()
        db.query(Employee).filter(Employee.company_id == company.id).delete()
        db.query(Company).filter(Company.id == company.id).delete()
        db.commit()
        db.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("All settings checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
