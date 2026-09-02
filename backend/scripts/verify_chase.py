"""Verification: the chase ladder and its terminal state.

Not a test suite — a runnable check that the guarantees the chase layer claims are
real. Creates a throwaway company, asserts against it, and deletes it.

    python -m scripts.verify_chase
"""

import sys
import uuid
from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models import Company, Employee, Task, TaskStatus
from app.models.enums import ReportedVia
from app.models.status_update import StatusUpdate
from app.schemas.task import StatusUpdateCreate, TaskUpdate
from app.services.chase_service import due_for_chase, run_chase_cycle
from app.services.task_service import TaskService

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}{f'  — {detail}' if detail else ''}")
    if not condition:
        FAILURES.append(label)


def make_task(db, company, employee, *, title, deadline=None, age_days=0, status=TaskStatus.APPROVED):
    """A task whose clock started `age_days` ago."""
    created = datetime.now(UTC) - timedelta(days=age_days)
    task = Task(
        company_id=company.id,
        title=title,
        status=status,
        owner_employee_id=employee.id if employee else None,
        deadline=deadline,
        idempotency_key=f"verify-{uuid.uuid4()}",
        created_at=created,
        delegated_at=created,
    )
    db.add(task)
    db.flush()
    return task


def main() -> int:  # noqa: C901 - a linear script of assertions
    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    company = Company(name=f"chase-verify-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()

    alice = Employee(company_id=company.id, name="Alice", role_title="Eng")
    db.add(alice)
    db.flush()

    now = datetime.now(UTC)
    try:
        print("\n1. Trigger — who is due for a chase")
        quiet = make_task(db, company, alice, title="quiet, no deadline", age_days=5)
        fresh = make_task(db, company, alice, title="fresh, no deadline", age_days=1)
        overdue = make_task(
            db, company, alice, title="overdue", age_days=1,
            deadline=now - timedelta(days=2),
        )
        unowned = make_task(db, company, None, title="nobody owns this", age_days=9)
        blocked = make_task(
            db, company, alice, title="blocked", age_days=9, status=TaskStatus.BLOCKED
        )
        done = make_task(db, company, alice, title="done", age_days=9, status=TaskStatus.DONE)

        due = {t.id for t in due_for_chase(db, company, now)}
        check("silent past cadence is chased", quiet.id in due)
        check("silent within cadence is not", fresh.id not in due)
        check("overdue is chased even though recently touched", overdue.id in due)
        check("unowned is never chased", unowned.id not in due, "nobody to chase")
        check("blocked is never chased", blocked.id not in due, "already answered")
        check("done is never chased", done.id not in due)

        print("\n2. Ladder — two chases, then handed to the founder")
        r1 = run_chase_cycle(db, company, now)
        check("first cycle reminds", r1.reminded >= 2, f"reminded={r1.reminded}")
        db.refresh(quiet)
        check("chase_count incremented", quiet.chase_count == 1, f"={quiet.chase_count}")
        check("not escalated after one chase", quiet.escalated is False)

        again = run_chase_cycle(db, company, now)
        check("re-running immediately is a no-op", again.reminded == 0, "Rule 3, idempotent")

        later = now + timedelta(days=4)
        r2 = run_chase_cycle(db, company, later)
        db.refresh(quiet)
        check("second chase after another cadence", quiet.chase_count == 2)
        check("escalated at the limit", quiet.escalated is True, f"max_chases={company.max_chases}")
        check("escalation counted", r2.escalated >= 1)

        # Far future, so anything still eligible would certainly be chased. The
        # claim under test is that *this* task is finished with, not that the cycle
        # is idle — other tasks going quiet in the meantime is correct behaviour.
        run_chase_cycle(db, company, later + timedelta(days=10))
        db.refresh(quiet)
        check("never chased past the limit", quiet.chase_count == 2, "ladder terminates")
        check("exhausted task stays escalated", quiet.escalated is True)

        print("\n3. Reminders are visible to the employee")
        notes = db.query(StatusUpdate).filter(StatusUpdate.task_id == quiet.id).all()
        agent_notes = [n for n in notes if n.reported_via is ReportedVia.AGENT]
        check("reminder written to the timeline", len(agent_notes) == 2, f"{len(agent_notes)} entries")
        check("reminder does not change status", all(n.status is TaskStatus.APPROVED for n in agent_notes))
        if agent_notes:
            print(f"        note: {agent_notes[0].note!r}")

        print("\n4. Employee response")
        svc = TaskService(db, company.id)

        # A fresh task with budget still on the clock, so "blocked escalates before
        # the limit" is genuinely tested rather than reading a flag the ladder had
        # already set. Chased exactly once first.
        early = make_task(db, company, alice, title="blocks early", age_days=5)
        run_chase_cycle(db, company, now)
        db.refresh(early)
        check("chased once per cadence, not once per run", early.chase_count == 1,
              f"={early.chase_count}")
        check("one chase is below the limit", early.escalated is False)
        before = early.chase_count

        svc.record_status(early.id, StatusUpdateCreate(
            status=TaskStatus.BLOCKED, note="waiting on legal",
            reported_by_employee_id=alice.id, reported_via=ReportedVia.DASHBOARD,
        ))
        db.refresh(early)
        check("blocked hands straight to the founder", early.escalated is True,
              "before the limit was reached")
        check("blocked keeps its spent budget", early.chase_count == before)

        print("\n5. Founder reset")
        svc.update(early.id, TaskUpdate(title="blocks early (renamed)"))
        db.refresh(early)
        check("cosmetic edit does NOT grant a fresh budget", early.chase_count == before)
        check("cosmetic edit leaves it escalated", early.escalated is True)

        svc.update(early.id, TaskUpdate(status=TaskStatus.IN_PROGRESS))
        db.refresh(early)
        overdue = early  # the remaining assertions read this task
        check("founder unblock resets the budget", overdue.chase_count == 0)
        check("founder unblock clears escalation", overdue.escalated is False)
        check("founder unblock restarts the clock", overdue.last_chased_at is None)

        print("\n6. Employee resuming clears escalation but not the budget")
        db.refresh(quiet)
        svc.record_status(quiet.id, StatusUpdateCreate(
            status=TaskStatus.IN_PROGRESS, note="on it",
            reported_by_employee_id=alice.id, reported_via=ReportedVia.DASHBOARD,
        ))
        db.refresh(quiet)
        check("responding drops it off the founder's list", quiet.escalated is False)
        check("responding does not mint new chases", quiet.chase_count == 2)

    finally:
        db.rollback()
        db.query(StatusUpdate).filter(StatusUpdate.company_id == company.id).delete()
        db.query(Task).filter(Task.company_id == company.id).delete()
        db.query(Employee).filter(Employee.company_id == company.id).delete()
        db.query(Company).filter(Company.id == company.id).delete()
        db.commit()
        db.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("All chase checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
