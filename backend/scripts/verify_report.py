"""Verification: the founder briefing.

Builds a throwaway company with a task in each state, generates a report, and
asserts the sections say what they claim. Cleans up after itself.

    python -m scripts.verify_report
"""

import json
import sys
import uuid
from datetime import UTC, datetime, timedelta

from app.database import SessionLocal
from app.models import Company, Employee, Task, TaskStatus
from app.models.enums import ReportedVia
from app.models.report import Report
from app.models.status_update import StatusUpdate
from app.services.report_service import SECTION_CAP, generate_report

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{f'  — {detail}' if detail else ''}")
    if not condition:
        FAILURES.append(label)


def main() -> int:  # noqa: C901
    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    company = Company(name=f"report-verify-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()
    alice = Employee(company_id=company.id, name="Alice", role_title="Eng")
    db.add(alice)
    db.flush()
    now = datetime.now(UTC)

    def task(title, **kw):
        t = Task(
            company_id=company.id, title=title,
            owner_employee_id=kw.pop("owner", alice.id),
            idempotency_key=f"rv-{uuid.uuid4()}",
            source_quote=kw.pop("quote", "we agreed Alice would handle it"),
            **kw,
        )
        db.add(t)
        db.flush()
        return t

    try:
        escalated = task("chased out", status=TaskStatus.APPROVED, chase_count=2, escalated=True)
        blocked = task("stuck on legal", status=TaskStatus.BLOCKED)
        overdue = task("late thing", status=TaskStatus.APPROVED,
                       deadline=now - timedelta(days=3))
        soon = task("due tomorrow", status=TaskStatus.APPROVED,
                    deadline=now + timedelta(hours=20))
        later = task("due next month", status=TaskStatus.APPROVED,
                     deadline=now + timedelta(days=30))
        quiet = task("chased once", status=TaskStatus.IN_PROGRESS, chase_count=1,
                     last_chased_at=now - timedelta(days=1))
        unowned = task("nobody owns this", status=TaskStatus.APPROVED, owner=None)
        done = task("finished", status=TaskStatus.DONE)

        moved_task = task("alice replied", status=TaskStatus.IN_PROGRESS)
        db.add(StatusUpdate(
            company_id=company.id, task_id=moved_task.id, status=TaskStatus.IN_PROGRESS,
            note="started", reported_by_employee_id=alice.id,
            reported_via=ReportedVia.DASHBOARD,
        ))
        # An agent reminder must not count as movement.
        db.add(StatusUpdate(
            company_id=company.id, task_id=quiet.id, status=TaskStatus.IN_PROGRESS,
            note="Reminder 1 of 2", reported_by_employee_id=None,
            reported_via=ReportedVia.AGENT,
        ))
        db.flush()

        report = generate_report(db, company, now)
        sections = {s["key"]: s for s in report.sections["sections"]}

        print("\n1. Needs your decision")
        ids = {i["task_id"] for i in sections["needs_decision"]["items"]}
        check("escalated task appears", str(escalated.id) in ids)
        check("blocked task appears", str(blocked.id) in ids)
        check("healthy task does not", str(later.id) not in ids)
        reasons = {i["task_id"]: i["reason"] for i in sections["needs_decision"]["items"]}
        check("reason explains why", "reminder" in reasons.get(str(escalated.id), "").lower(),
              reasons.get(str(escalated.id), ""))

        print("\n2. Slipping")
        ids = {i["task_id"] for i in sections["slipping"]["items"]}
        check("overdue appears", str(overdue.id) in ids)
        check("due within 48h appears", str(soon.id) in ids)
        check("due next month does not", str(later.id) not in ids)
        check("already-escalated is not repeated", str(escalated.id) not in ids)
        od = [i for i in sections["slipping"]["items"] if i["task_id"] == str(overdue.id)]
        check("overdue_days computed", od and od[0]["overdue_days"] == 3,
              f"={od[0]['overdue_days'] if od else None}")

        print("\n3. Moved")
        ids = {i["task_id"] for i in sections["moved"]["items"]}
        check("employee response counts as movement", str(moved_task.id) in ids)
        check("agent reminder does NOT", str(quiet.id) not in ids, "our own nudge is not news")

        print("\n4. Quiet")
        ids = {i["task_id"] for i in sections["quiet"]["items"]}
        check("chased-but-silent appears", str(quiet.id) in ids)
        check("never-chased does not", str(later.id) not in ids)
        q = [i for i in sections["quiet"]["items"] if i["task_id"] == str(quiet.id)]
        check("shows chase progress", q and q[0]["chases"] == "1 of 2",
              q[0]["chases"] if q else "")

        print("\n5. Counts and hygiene")
        c = report.counts
        check("done excluded from open", str(done.id) not in {
            i["task_id"] for s in sections.values() for i in s["items"]
        })
        check("unowned counted", c["unowned"] == 1, f"={c['unowned']}")
        check("blocked counted", c["blocked"] == 1, f"={c['blocked']}")
        check("awaiting_you counted", c["awaiting_you"] == 1, f"={c['awaiting_you']}")
        # Nine tasks created, one of them done. Terminal work is never live.
        check("open excludes terminal", c["open"] == 8, f"={c['open']}")
        check("every item cites its source", all(
            i.get("source_quote") for s in sections.values() for i in s["items"]
        ), "Rule 6")
        check("sections capped", all(
            len(s["items"]) <= SECTION_CAP for s in sections.values()
        ))
        check("empty text always present", all(s["empty"] for s in sections.values()))

        print("\n6. Regeneration is idempotent")
        first_id = report.id
        again = generate_report(db, company, now + timedelta(minutes=5))
        db.flush()
        check("same row updated, not appended", again.id == first_id)
        rows = db.query(Report).filter(Report.company_id == company.id).count()
        check("one report per day", rows == 1, f"rows={rows}")
        check("generated_at moved", again.generated_at > now)

        print(f"\n  counts: {json.dumps(report.counts)}")

    finally:
        db.rollback()
        db.query(Report).filter(Report.company_id == company.id).delete()
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
    print("All report checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
