"""Verification: email delegation, reminders, blockers, and one-tap action links.

    python -m scripts.verify_email_chase

Runs a throwaway SMTP server in-process (standard library only), points Sentinel
at it, and drives the real HTTP surface - so what is checked is the message that
would actually leave the building, not a mock of it.
"""

import email
import email.policy
import re
import socketserver
import sys
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.core.action_tokens import issue_action_token, verify_action_token
from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Company, Employee, Task, TaskStatus, User, UserRole
from app.models.approval import Approval
from app.models.enums import ReportedVia
from app.models.status_update import StatusUpdate
from app.services.task_service import TaskService

FAILURES: list[str] = []
INBOX: list[email.message.EmailMessage] = []
_INBOX_LOCK = threading.Lock()


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{f'  - {detail}' if detail else ''}")
    if not condition:
        FAILURES.append(label)


# --- a minimal SMTP sink -------------------------------------------------------


class _SmtpSink(socketserver.StreamRequestHandler):
    """Speaks just enough SMTP for smtplib to deliver, and keeps what arrives."""

    def handle(self) -> None:
        def reply(line: str) -> None:
            self.wfile.write((line + "\r\n").encode())

        reply("220 sink ready")
        in_data, lines = False, []
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            text = raw.decode("utf-8", "replace").rstrip("\r\n")
            if in_data:
                if text == ".":
                    in_data = False
                    message = email.message_from_string(
                        "\n".join(lines), policy=email.policy.default
                    )
                    with _INBOX_LOCK:
                        INBOX.append(message)
                    lines = []
                    reply("250 queued")
                else:
                    lines.append(text[1:] if text.startswith("..") else text)
                continue
            verb = text[:4].upper()
            if verb == "DATA":
                in_data = True
                reply("354 end with .")
            elif verb == "QUIT":
                reply("221 bye")
                return
            else:
                reply("250 ok")


def _start_sink() -> tuple[socketserver.ThreadingTCPServer, int]:
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _SmtpSink)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _wait_for(count: int, timeout: float = 5.0) -> list[email.message.EmailMessage]:
    """Mail is sent on a background thread - give it a moment to land."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with _INBOX_LOCK:
            if len(INBOX) >= count:
                return list(INBOX)
        time.sleep(0.05)
    with _INBOX_LOCK:
        return list(INBOX)


def _drain() -> None:
    time.sleep(0.3)
    with _INBOX_LOCK:
        INBOX.clear()


def _html(message: email.message.EmailMessage) -> str:
    return message.get_body(preferencelist=("html",)).get_content()


def _text(message: email.message.EmailMessage) -> str:
    return message.get_body(preferencelist=("plain",)).get_content()


def _token_from(message: email.message.EmailMessage) -> str | None:
    found = re.search(r"/act/([A-Za-z0-9_\-\.]+)\?s=", _text(message))
    return found.group(1) if found else None


# --- scenario ------------------------------------------------------------------


def main() -> int:
    sink, port = _start_sink()
    saved = {
        k: getattr(settings, k)
        for k in ("smtp_host", "smtp_port", "smtp_starttls", "smtp_use_ssl",
                  "smtp_username", "email_from", "app_base_url", "environment",
                  "jwt_secret_key")
    }
    settings.smtp_host = "127.0.0.1"
    settings.smtp_port = port
    settings.smtp_starttls = False
    settings.smtp_use_ssl = False
    settings.smtp_username = ""
    settings.email_from = "Sentinel <sentinel@verify.example>"
    settings.app_base_url = "https://app.verify.example"

    db = SessionLocal()
    client = TestClient(app)
    tag = uuid.uuid4().hex[:8]
    companies: list[uuid.UUID] = []

    def make_company(name: str) -> tuple[Company, User, dict]:
        company = Company(name=name, escalation_after_days=3, max_chases=2)
        db.add(company)
        db.flush()
        founder = User(
            company_id=company.id, email=f"founder-{name}@verify.example",
            password_hash=hash_password("x" * 12), role=UserRole.FOUNDER,
            full_name="Ayesha Khan",
        )
        db.add(founder)
        db.flush()
        companies.append(company.id)
        token = create_access_token(user_id=founder.id, company_id=company.id, role=founder.role)
        return company, founder, {"Authorization": f"Bearer {token}"}

    try:
        company, founder, fh = make_company(f"mail-{tag}")
        bilal = Employee(company_id=company.id, name="Bilal Ahmed",
                         email=f"bilal-{tag}@verify.example")
        sara = Employee(company_id=company.id, name="Sana Malik",
                        email=f"sana-{tag}@verify.example")
        ghost = Employee(company_id=company.id, name="No Email")
        db.add_all([bilal, sara, ghost])
        db.flush()
        bilal_user = User(
            company_id=company.id, email=f"bilal-login-{tag}@verify.example",
            password_hash=hash_password("x" * 12), role=UserRole.EMPLOYEE,
            full_name="Bilal Ahmed", employee_id=bilal.id,
        )
        db.add(bilal_user)
        db.commit()
        eh = {"Authorization": "Bearer " + create_access_token(
            user_id=bilal_user.id, company_id=company.id, role=bilal_user.role)}

        tasks = TaskService(db, company.id)

        # ---------------------------------------------------------------- 1
        print("\n1. Approval emails the owner, and starts their clock")
        task, _ = tasks.create_pending(
            title="Send <b>Meridian</b> dataset",
            idempotency_key=f"verify-mail-{tag}-1",
            source_quote="Hamza, can you get the <script>alert(1)</script> dataset by Thursday?",
            source_ref="Meeting: Weekly Delivery Standup",
            owner_employee_id=bilal.id,
            deadline=datetime.now(UTC) + timedelta(days=3),
        )
        db.commit()
        approval_id = task.approval.id

        r = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=fh)
        check("approve succeeds", r.status_code == 200, f"HTTP {r.status_code}")
        inbox = _wait_for(1)
        check("exactly one email sent", len(inbox) == 1, f"{len(inbox)} sent")
        mail = inbox[0] if inbox else None
        if mail is not None:
            check("addressed to the owner", bilal.email in mail["To"], mail["To"])
            check("subject names the commitment",
                  mail["Subject"] == "New commitment: Send <b>Meridian</b> dataset",
                  mail["Subject"])
            html = _html(mail)
            check("HTML escapes the title", "&lt;b&gt;Meridian&lt;/b&gt;" in html
                  and "<b>Meridian</b>" not in html)
            check("HTML escapes the quote - no script tag survives",
                  "<script>" not in html and "&lt;script&gt;" in html)
            check("names who asked", "Ayesha Khan asked you" in html)
            check("names the source meeting", "Weekly Delivery Standup" in html)
            check("carries all three one-tap links",
                  all(f"?s={s}" in html for s in ("done", "in_progress", "blocked")))
            check("links point at the app", "https://app.verify.example/act/" in html)
            check("marked auto-generated (stops out-of-office loops)",
                  mail["Auto-Submitted"] == "auto-generated")
            check("plain-text part present for every link",
                  _text(mail).count("https://app.verify.example/act/") == 3)
        db.expire_all()
        fresh = db.get(Task, task.id)
        check("delegated_at stamped at approval", fresh.delegated_at is not None)
        check("delegated_at equals the decision time",
              fresh.delegated_at == fresh.approval.decided_at)

        # ---------------------------------------------------------------- 2
        print("\n2. The link previews without changing anything")
        token = _token_from(mail) if mail is not None else None
        check("token found in the email", token is not None)
        before = db.scalar(select(StatusUpdate.id).where(StatusUpdate.task_id == task.id).limit(1))
        r = client.get(f"/api/v1/actions/{token}")
        check("preview returns 200", r.status_code == 200, f"HTTP {r.status_code}")
        body = r.json()
        check("preview shows the task", body.get("title") == task.title)
        check("preview shows the owner", body.get("owner_name") == "Bilal Ahmed")
        check("preview is not closed", body.get("closed") is False)
        db.expire_all()
        check("GET did not change the status (link scanners are safe)",
              db.get(Task, task.id).status is TaskStatus.APPROVED)
        check("GET wrote no timeline entry",
              db.scalar(select(StatusUpdate.id).where(StatusUpdate.task_id == task.id).limit(1))
              == before)

        # ---------------------------------------------------------------- 3
        print("\n3. Tapping records the answer as the owner, via email")
        r = client.post(f"/api/v1/actions/{token}", json={"status": "in_progress"})
        check("in progress accepted", r.status_code == 200 and r.json()["changed"] is True,
              f"HTTP {r.status_code} {r.text[:120]}")
        db.expire_all()
        entries = db.scalars(
            select(StatusUpdate).where(StatusUpdate.task_id == task.id)
        ).all()
        check("one timeline entry", len(entries) == 1, f"{len(entries)}")
        if entries:
            check("recorded as reported via email", entries[0].reported_via is ReportedVia.EMAIL)
            check("recorded as reported by the owner",
                  entries[0].reported_by_employee_id == bilal.id)

        r = client.post(f"/api/v1/actions/{token}", json={"status": "in_progress"})
        check("double tap is a quiet success", r.status_code == 200 and r.json()["changed"] is False)
        db.expire_all()
        check("double tap adds no second entry",
              len(db.scalars(select(StatusUpdate).where(StatusUpdate.task_id == task.id)).all()) == 1)

        # ---------------------------------------------------------------- 4
        print("\n4. Blocked from email reaches the founder")
        _drain()
        r = client.post(f"/api/v1/actions/{token}",
                        json={"status": "blocked", "note": "Still no dataset <from> Meridian"})
        check("blocked accepted", r.status_code == 200, f"HTTP {r.status_code}")
        inbox = _wait_for(1)
        founder_mail = [m for m in inbox if founder.email in m["To"]]
        check("founder emailed about the blocker", len(founder_mail) == 1, f"{len(inbox)} sent")
        if founder_mail:
            check("blocker subject", founder_mail[0]["Subject"].startswith("Blocked: "))
            fhtml = _html(founder_mail[0])
            check("carries the employee's note, escaped",
                  "Still no dataset &lt;from&gt; Meridian" in fhtml)
            check("names who is blocked", "Bilal Ahmed is blocked" in fhtml)
        db.expire_all()
        check("task is escalated to the founder", db.get(Task, task.id).escalated is True)

        r = client.post(f"/api/v1/actions/{token}", json={"status": "done"})
        check("done accepted", r.status_code == 200)
        r = client.post(f"/api/v1/actions/{token}", json={"status": "blocked"})
        check("a closed task refuses further changes", r.status_code == 409, f"HTTP {r.status_code}")
        r = client.get(f"/api/v1/actions/{token}")
        check("preview reports it closed", r.status_code == 200 and r.json()["closed"] is True)

        # ---------------------------------------------------------------- 5
        print("\n5. Links are bound, signed, and expire")
        r = client.post(f"/api/v1/actions/{token}", json={"status": "archived"})
        check("an unknown status is rejected", r.status_code in (400, 422), f"HTTP {r.status_code}")
        check("garbage token is 404", client.get("/api/v1/actions/not-a-token").status_code == 404)

        session_token = fh["Authorization"].split()[1]
        check("a session token is not an action link",
              client.get(f"/api/v1/actions/{session_token}").status_code == 404)
        check("an action link is not a session token",
              client.get("/api/v1/me/tasks",
                         headers={"Authorization": f"Bearer {token}"}).status_code == 401)

        expired = issue_action_token(task_id=task.id, employee_id=bilal.id,
                                     company_id=company.id, ttl=timedelta(seconds=-1))
        r = client.get(f"/api/v1/actions/{expired}")
        check("expired link is 410 with its own message", r.status_code == 410,
              f"HTTP {r.status_code}")

        other, _, _ = make_company(f"mail-other-{tag}")
        db.commit()
        cross = issue_action_token(task_id=task.id, employee_id=bilal.id, company_id=other.id)
        check("a link minted for another tenant cannot reach this task",
              client.get(f"/api/v1/actions/{cross}").status_code == 404)

        old_key = settings.jwt_secret_key
        settings.jwt_secret_key = old_key + "-rotated"
        check("rotating the secret invalidates old links", verify_action_token(token) is None)
        settings.jwt_secret_key = old_key

        # ---------------------------------------------------------------- 6
        print("\n6. Reassignment hands the task over, and retires the old link")
        _drain()
        t2, _ = tasks.create_pending(
            title="Draft renewal talking points", idempotency_key=f"verify-mail-{tag}-2",
            source_quote="Sana, draft the renewal talking points.", owner_employee_id=bilal.id,
        )
        db.commit()
        client.post(f"/api/v1/approvals/{t2.approval.id}/approve", headers=fh)
        first = _wait_for(1)
        old_link = _token_from(first[0]) if first else None
        _drain()
        r = client.patch(f"/api/v1/tasks/{t2.id}", headers=fh,
                         json={"owner_employee_id": str(sara.id)})
        check("reassign succeeds", r.status_code == 200, f"HTTP {r.status_code}")
        inbox = _wait_for(1)
        check("new owner is emailed", any(sara.email in m["To"] for m in inbox), f"{len(inbox)} sent")
        check("old owner is not emailed again", not any(bilal.email in m["To"] for m in inbox))
        r = client.post(f"/api/v1/actions/{old_link}", json={"status": "done"})
        check("old owner's link now refuses", r.status_code == 409, f"HTTP {r.status_code}")
        db.expire_all()
        check("reassignment restarts the clock", db.get(Task, t2.id).delegated_at is not None)

        _drain()
        r = client.patch(f"/api/v1/tasks/{t2.id}", headers=fh, json={"title": "Draft renewal notes"})
        check("an edit that keeps the owner sends nothing", len(_wait_for(1, timeout=1.0)) == 0)

        # ---------------------------------------------------------------- 7
        print("\n7. The chase emails its reminders")
        _drain()
        t3 = Task(
            company_id=company.id, title="Evaluation harness", status=TaskStatus.APPROVED,
            owner_employee_id=bilal.id, idempotency_key=f"verify-mail-{tag}-3",
            source_quote="I can have the harness finished by the twenty-second.",
            deadline=datetime.now(UTC) - timedelta(days=2),
            delegated_at=datetime.now(UTC) - timedelta(days=5),
        )
        db.add(t3)
        db.commit()
        r = client.post("/api/v1/admin/run-chase", headers=fh)
        check("chase runs", r.status_code == 200 and r.json()["reminded"] >= 1, r.text[:120])
        inbox = _wait_for(1)
        reminder = [m for m in inbox if "Evaluation harness" in m["Subject"]]
        check("owner gets the reminder", len(reminder) == 1, f"{len(inbox)} sent")
        if reminder:
            check("subject shows the ladder", reminder[0]["Subject"] == "Reminder 1 of 2: Evaluation harness",
                  reminder[0]["Subject"])
            check("says how late it is", "Was due 2 days ago" in _html(reminder[0]))
            check("reminder carries one-tap links", _token_from(reminder[0]) is not None)
        _drain()
        client.post("/api/v1/admin/run-chase", headers=fh)
        check("running it again sends nothing (rate limit holds)",
              len(_wait_for(1, timeout=1.0)) == 0)

        # ---------------------------------------------------------------- 8
        print("\n8. In-app answers behave the same as email")
        _drain()
        t4 = Task(
            company_id=company.id, title="Pull performance numbers", status=TaskStatus.APPROVED,
            owner_employee_id=bilal.id, idempotency_key=f"verify-mail-{tag}-4",
            source_quote="Bilal, send Sana the numbers by Friday.",
        )
        db.add(t4)
        db.commit()
        r = client.post(f"/api/v1/me/tasks/{t4.id}/status", headers=eh,
                        json={"status": "blocked", "note": "Waiting on prod access"})
        check("in-app blocked accepted", r.status_code == 200, f"HTTP {r.status_code}")
        inbox = _wait_for(1)
        check("founder emailed for an in-app blocker too",
              any(founder.email in m["To"] for m in inbox), f"{len(inbox)} sent")

        # ---------------------------------------------------------------- 9
        print("\n9. Founder-typed tasks, missing addresses, and email switched off")
        _drain()
        r = client.post("/api/v1/tasks", headers=fh,
                        json={"title": "Update pricing page", "owner_employee_id": str(sara.id)})
        check("typed task created", r.status_code == 201, f"HTTP {r.status_code}")
        check("its owner is emailed", any(sara.email in m["To"] for m in _wait_for(1)))

        _drain()
        r = client.post("/api/v1/tasks", headers=fh, json={"title": "Nobody owns this yet"})
        check("an unowned task sends nothing", len(_wait_for(1, timeout=1.0)) == 0)

        _drain()
        t5, _ = tasks.create_pending(title="Ghost task", idempotency_key=f"verify-mail-{tag}-5",
                                     source_quote="Someone should do this.", owner_employee_id=ghost.id)
        db.commit()
        r = client.post(f"/api/v1/approvals/{t5.approval.id}/approve", headers=fh)
        check("approving for someone with no address still succeeds", r.status_code == 200)
        check("and sends nothing", len(_wait_for(1, timeout=1.0)) == 0)

        _drain()
        settings.smtp_host = ""
        t6, _ = tasks.create_pending(title="Quiet task", idempotency_key=f"verify-mail-{tag}-6",
                                     source_quote="Bilal, one more.", owner_employee_id=bilal.id)
        db.commit()
        r = client.post(f"/api/v1/approvals/{t6.approval.id}/approve", headers=fh)
        check("with email unconfigured, approval still succeeds", r.status_code == 200)
        check("and nothing is sent", len(_wait_for(1, timeout=1.0)) == 0)
        settings.smtp_host = "127.0.0.1"

        # ---------------------------------------------------------------- 10
        print("\n10. Production refuses the placeholder signing key")
        settings.environment = "production"
        settings.jwt_secret_key = "change-me-generate-a-real-random-value"
        refused = False
        try:
            with TestClient(app):
                pass
        except RuntimeError as exc:
            refused = "JWT_SECRET_KEY" in str(exc)
        check("startup refuses the default key in production", refused)
        settings.environment = saved["environment"]
        settings.jwt_secret_key = saved["jwt_secret_key"]

    finally:
        db.rollback()
        for cid in companies:
            for model in (StatusUpdate, Approval, Task):
                db.query(model).filter(model.company_id == cid).delete()
            db.query(User).filter(User.company_id == cid).delete()
            db.query(Employee).filter(Employee.company_id == cid).delete()
            db.query(Company).filter(Company.id == cid).delete()
        db.commit()
        db.close()
        for key, value in saved.items():
            setattr(settings, key, value)
        sink.shutdown()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("All email chase checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
