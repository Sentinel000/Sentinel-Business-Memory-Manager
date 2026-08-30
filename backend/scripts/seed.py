"""Seed the demo tenant.

Idempotent: re-running updates the existing company rather than creating a second.

    python -m scripts.seed
"""

import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import Company, Employee, User, UserRole

DEMO_COMPANY = "Northwind SaaS"
# .example is reserved for documentation (RFC 2606) and passes email-validator.
# A .test address does NOT - it is rejected before the password is ever checked.
FOUNDER_EMAIL = "sarah@northwind.example"
FOUNDER_PASSWORD = "sentinel-demo-2026"  # noqa: S105 - local seed data only

PERSONA = {
    "assistant_name": "Sentinel",
    "tone": "direct",
    "company_context": (
        "25-person B2B SaaS. Sarah is founder/CEO. Mark runs sales, Lisa runs "
        "marketing, John leads engineering. All three report to Sarah."
    ),
    "glossary": {"ACV": "annual contract value", "Q4": "fiscal Q4, Oct-Dec"},
}


def main() -> int:
    db = SessionLocal()
    try:
        company = db.execute(
            select(Company).where(Company.name == DEMO_COMPANY)
        ).scalar_one_or_none()

        if company is None:
            company = Company(name=DEMO_COMPANY, persona_config=PERSONA, escalation_after_days=3)
            db.add(company)
            db.flush()
            print(f"created company {company.name} ({company.id})")
        else:
            company.persona_config = PERSONA
            print(f"company exists {company.name} ({company.id})")

        # Employees first — the org chart exists before anyone has a login.
        existing = {
            e.name: e
            for e in db.execute(
                select(Employee).where(Employee.company_id == company.id)
            ).scalars()
        }

        def ensure_employee(name: str, role_title: str, manager: Employee | None) -> Employee:
            employee = existing.get(name)
            if employee is None:
                employee = Employee(
                    company_id=company.id,
                    name=name,
                    role_title=role_title,
                    manager_id=manager.id if manager else None,
                )
                db.add(employee)
                db.flush()
                existing[name] = employee
                print(f"  + employee {name} ({role_title})")
            return employee

        sarah = ensure_employee("Sarah Chen", "Founder / CEO", None)
        ensure_employee("Mark Rivera", "Head of Sales", sarah)
        ensure_employee("Lisa Okafor", "Marketing Manager", sarah)
        ensure_employee("John Adeyemi", "Engineering Lead", sarah)

        # slack_user_id stays null until the step-2 member-list pull. Delegation has
        # to handle an unmapped owner, so the seed does not fake one.

        founder = db.execute(
            select(User).where(User.company_id == company.id, User.email == FOUNDER_EMAIL)
        ).scalar_one_or_none()

        if founder is None:
            db.add(
                User(
                    company_id=company.id,
                    email=FOUNDER_EMAIL,
                    password_hash=hash_password(FOUNDER_PASSWORD),
                    full_name="Sarah Chen",
                    role=UserRole.FOUNDER,
                    employee_id=sarah.id,
                )
            )
            print(f"  + founder login {FOUNDER_EMAIL}")
        else:
            print(f"  founder login exists {FOUNDER_EMAIL}")

        db.flush()

        # A task waiting on approval, so the queue is not empty before the extractor
        # exists. Shaped exactly as the extractor will write one: a verbatim quote, a
        # source, a confidence score, and no promotion — it falls to the
        # pending_approval default.
        from app.services.task_service import TaskService

        service = TaskService(db, company.id)
        mark = existing.get("Mark Rivera")
        _, created_pending = service.create_pending(
            title="Send Sarah the Q4 forecast",
            idempotency_key="seed:sales-standup:q4-forecast",
            source_quote="Mark, can you get me the Q4 forecast by Friday?",
            source_ref="Sales Standup, Tue 10:04",
            owner_employee_id=mark.id if mark else None,
            deadline=datetime.now(UTC) + timedelta(days=2),
            confidence=0.91,
        )
        if created_pending:
            print("  + pending task awaiting approval")

        db.commit()
        print(f"\nseeded. log in as {FOUNDER_EMAIL} / {FOUNDER_PASSWORD}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
