"""Verification: WhatsApp chat import - parsing, windowing, and the import endpoint.

    python -m scripts.verify_whatsapp_import

Needs a database but no Qwen key: the extractor call is replaced by a recorder, so
what is checked is exactly what the extractor would be handed - the transcript,
its dates, the source label, and the prompt variant.
"""

import io
import sys
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.meeting_service as meeting_service
from app.agentic_ai.prompts import extractor as extractor_prompt
from app.core.security import create_access_token, hash_password
from app.database import SessionLocal
from app.main import app
from app.models import Company, Employee, User, UserRole
from app.models.meeting import Meeting, TranscriptSegment
from app.services import whatsapp_import as wa

FAILURES: list[str] = []
DEMO = Path(__file__).resolve().parents[2] / "docs" / "demo" / "WhatsApp Chat with Delivery Team.txt"


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}{f'  - {detail}' if detail else ''}")
    if not condition:
        FAILURES.append(label)


def main() -> int:
    # ---------------------------------------------------------------- 1
    print("\n1. The bundled demo chat (Android export, Roman Urdu and English)")
    text = DEMO.read_text(encoding="utf-8")
    chat = wa.parse_export(text)
    msgs = chat.messages
    check("reads every timestamped line", chat.entries_seen == 31, f"{chat.entries_seen}")
    check("keeps the 26 real messages", len(msgs) == 26, f"{len(msgs)}")
    check("drops system lines (encryption notice, group created, members added)",
          not any("end-to-end" in m.text or "created group" in m.text for m in msgs))
    check("drops <Media omitted> and deleted messages",
          not any(m.text in ("<Media omitted>", "This message was deleted") for m in msgs))
    check("strips the <This message was edited> marker",
          any(m.text == "Ji abhi call karta hoon" for m in msgs))
    multi = [m for m in msgs if m.text.startswith("Ayesha, dataset abhi tak")]
    check("joins a message that spans two lines",
          len(multi) == 1 and "kal bhi reply nahi kiya" in multi[0].text)
    check("reads the order as day-first", chat.day_first is True)
    check("knows exactly who said what",
          {m.sender for m in msgs} == {"Ayesha Khan", "Bilal Ahmed", "Hamza Sheikh", "Sana Malik"})
    check("keeps emoji intact", any("\U0001f91e" in m.text for m in msgs))
    check("first message timestamp", msgs[0].at == datetime(2026, 9, 23, 10, 5))

    # ---------------------------------------------------------------- 2
    print("\n2. Windowing and rendering")
    check("7 days back from the newest message keeps the whole week",
          len(wa.recent(msgs, 7)) == 26)
    last_day = wa.recent(msgs, 1)
    check("1 day keeps only the last day", len(last_day) == 4 and
          all(m.at.date() == date(2026, 9, 29) for m in last_day), f"{len(last_day)}")
    check("2 days reaches back into Monday", len(wa.recent(msgs, 2)) == 5)
    rendered = wa.render_transcript(msgs).splitlines()
    check("one line per message", len(rendered) == 26)
    check("each line leads with its own date",
          rendered[0] == "[Wed 23 Sep 2026 10:05] Ayesha Khan: Assalam o alaikum team. "
                         "Meridian ka kaam is hafte close karna hai, saari updates yahin dein please",
          rendered[0][:60])
    check("a two-line message renders as one quotable line",
          any(line.endswith("mushkil hai Meridian ki team ne kal bhi reply nahi kiya")
              for line in rendered))

    # ---------------------------------------------------------------- 3
    print("\n3. Other phones and locales")
    ios = ("‎[29/09/2026, 9:50:12 AM] Bilal Ahmed: Dataset kal tak\n"
           "[29/09/2026, 9:51:00 PM] Ayesha Khan: ‎image omitted\n"
           "[29/09/2026, 12:05:00 AM] Sana Malik: late night\n"
           "[29/09/2026, 12:30:00 PM] Hamza Sheikh: lunch\n")
    c = wa.parse_export(ios)
    check("iPhone bracket format with seconds", len(c.messages) == 3, f"{len(c.messages)}")
    check("invisible direction marks removed", c.messages[0].sender == "Bilal Ahmed")
    check("'image omitted' dropped even with a hidden mark", all("omitted" not in m.text for m in c.messages))
    check("12-hour AM read correctly", c.messages[0].at == datetime(2026, 9, 29, 9, 50, 12))
    check("12 AM is midnight", c.messages[1].at.hour == 0)
    check("12 PM is noon", c.messages[2].at.hour == 12)

    us = ("9/29/26, 9:50 PM - Bilal Ahmed: x\n"
          "9/30/26, 10:00 AM - Ayesha Khan: y\n")
    c = wa.parse_export(us)
    check("US month-first order detected", c.day_first is False)
    check("narrow no-break space before PM handled", c.messages[0].at == datetime(2026, 9, 29, 21, 50))

    dotted = "29.09.26, 10:04 - Bilal Ahmed: dotted dates\n"
    check("dotted dates and 2-digit years",
          wa.parse_export(dotted).messages[0].at == datetime(2026, 9, 29, 10, 4))

    try:
        wa.parse_export("Meeting notes\nBilal will send the deck by Friday.")
        refused = False
    except wa.NotAWhatsAppExport as exc:
        refused = "Export chat" in str(exc)
    check("a non-WhatsApp file is refused, with instructions", refused)

    # ---------------------------------------------------------------- 4
    print("\n4. Files: names, zips and limits")
    check("Android file name gives the group", wa.group_name("WhatsApp Chat with Delivery Team.txt") == "Delivery Team")
    check("iPhone zip name gives the group", wa.group_name("WhatsApp Chat - Delivery Team.zip") == "Delivery Team")
    check("a bare _chat.txt has no group name", wa.group_name("_chat.txt") is None)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("_chat.txt", text)
        z.writestr("00000012-PHOTO.jpg", b"\xff\xd8")
    check("reads the chat out of an iPhone zip", wa.read_export(buf.getvalue(), "x.zip") == text)

    empty_zip = io.BytesIO()
    with zipfile.ZipFile(empty_zip, "w") as z:
        z.writestr("photo.jpg", b"\xff\xd8")
    try:
        wa.read_export(empty_zip.getvalue(), "x.zip")
        refused = False
    except wa.NotAWhatsAppExport:
        refused = True
    check("a zip with no chat inside is refused", refused)

    try:
        wa.read_export(b"x" * (wa.MAX_EXPORT_BYTES + 1), "big.txt")
        refused = False
    except wa.NotAWhatsAppExport:
        refused = True
    check("an oversized upload is refused", refused)
    check("a UTF-8 byte-order mark is dropped",
          wa.read_export("﻿".encode() + b"29/09/2026, 10:04 - A: b", "c.txt").startswith("29/"))

    # ---------------------------------------------------------------- 5
    print("\n5. The extractor prompt")
    saved_base = extractor_prompt.render_base_prompt
    extractor_prompt.render_base_prompt = lambda company: "BASE"
    try:
        p_wa = extractor_prompt.render_extractor_prompt(SimpleNamespace(), source_kind="whatsapp")
        p_mt = extractor_prompt.render_extractor_prompt(SimpleNamespace(), occurred_on=date(2026, 9, 29))
    finally:
        extractor_prompt.render_base_prompt = saved_base
    check("the model is told today's date", "Today is " in p_wa)
    check("WhatsApp lines are dated per message", "date of the message it appears in" in p_wa)
    check("Roman Urdu is named, quotes stay in the original",
          "Roman Urdu" in p_wa and "never translated" in p_wa)
    check("a meeting resolves against the day it happened",
          "Tuesday 29 September 2026" in p_mt and "WhatsApp" not in p_mt)

    # ---------------------------------------------------------------- 6
    print("\n6. The import endpoint (extractor swapped for a recorder)")
    calls: list[dict] = []
    real_extract = meeting_service.run_transcript_extraction

    def recorder(**kwargs):
        calls.append(kwargs)
        return {"summary": "recorded", "tasks_extracted": []}

    meeting_service.run_transcript_extraction = recorder

    db = SessionLocal()
    client = TestClient(app)
    tag = uuid.uuid4().hex[:8]
    company = Company(name=f"wa-verify-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()
    emp = Employee(company_id=company.id, name="Bilal Ahmed")
    db.add(emp)
    db.flush()
    founder = User(company_id=company.id, email=f"wa-f-{tag}@verify.example",
                   password_hash=hash_password("x" * 12), role=UserRole.FOUNDER, full_name="Ayesha Khan")
    staff = User(company_id=company.id, email=f"wa-e-{tag}@verify.example",
                 password_hash=hash_password("x" * 12), role=UserRole.EMPLOYEE, employee_id=emp.id)
    db.add_all([founder, staff])
    db.commit()
    fh = {"Authorization": "Bearer " + create_access_token(
        user_id=founder.id, company_id=company.id, role=founder.role)}
    eh = {"Authorization": "Bearer " + create_access_token(
        user_id=staff.id, company_id=company.id, role=staff.role)}

    def upload(data: bytes, name: str, headers: dict, days: str = "7"):
        return client.post("/api/v1/meetings/whatsapp", headers=headers,
                           files={"file": (name, data, "text/plain")}, data={"days": days})

    try:
        raw = DEMO.read_bytes()
        r = upload(raw, DEMO.name, fh)
        check("import succeeds", r.status_code == 201, f"HTTP {r.status_code} {r.text[:150]}")
        body = r.json() if r.status_code == 201 else {}
        check("named after the group", body.get("title") == "WhatsApp: Delivery Team", body.get("title"))
        check("extractor called once", len(calls) == 1, f"{len(calls)}")
        if calls:
            call = calls[0]
            lines = call["transcript_text"].splitlines()
            check("extractor gets the WhatsApp prompt", call.get("source_kind") == "whatsapp")
            check("tasks will cite the group", call.get("source_ref") == "WhatsApp: Delivery Team",
                  call.get("source_ref"))
            check("dated to the newest message", call.get("occurred_on") == date(2026, 9, 29),
                  str(call.get("occurred_on")))
            check("all 26 messages handed over", len(lines) == 26, f"{len(lines)}")
            check("every line carries sender and date",
                  all(line.startswith("[") and "] " in line and ": " in line for line in lines))

        db.expire_all()
        meeting = db.query(Meeting).filter(Meeting.company_id == company.id).first()
        check("recorded as a WhatsApp source", meeting is not None and meeting.audio_format == "whatsapp")
        check("keeps the original file name", meeting is not None and meeting.audio_filename == DEMO.name)

        calls.clear()
        r = upload(raw, DEMO.name, fh, days="1")
        check("a 1-day window hands over only that day",
              r.status_code == 201 and calls and len(calls[0]["transcript_text"].splitlines()) == 4)

        r = upload(b"Just some meeting notes, not a chat.", "notes.txt", fh)
        check("a wrong file gets a 400 with instructions",
              r.status_code == 400 and "Export chat" in r.json().get("error", ""), f"HTTP {r.status_code}")
        check("a wrong file does not reach the extractor", len(calls) == 1)

        r = upload(raw, DEMO.name, fh, days="0")
        check("a zero-day window is rejected", r.status_code in (400, 422), f"HTTP {r.status_code}")
        r = upload(raw, DEMO.name, eh)
        check("employees cannot import", r.status_code == 403, f"HTTP {r.status_code}")
        r = client.post("/api/v1/meetings/whatsapp", files={"file": ("a.txt", raw, "text/plain")})
        check("anonymous cannot import", r.status_code == 401, f"HTTP {r.status_code}")

        # ------------------------------------------------------------ 7
        print("\n7. Failures the browser can actually read")
        origin = {"Origin": "http://localhost:3000"}

        def model_down(**kwargs):
            raise RuntimeError("provider timeout")

        meeting_service.run_transcript_extraction = model_down
        r = upload(raw, DEMO.name, {**fh, **origin})
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        check("a model failure is a 502, not a bare 500", r.status_code == 502, f"HTTP {r.status_code}")
        check("with a message that says what happened",
              "could not reach the AI model" in body.get("error", ""), body.get("error", "")[:80])
        check("and the provider's own error is not echoed", "provider timeout" not in r.text)
        check("it carries CORS headers", r.headers.get("access-control-allow-origin") == origin["Origin"])

        real_recent = wa.recent
        wa.recent = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bug"))
        try:
            r = upload(raw, DEMO.name, {**fh, **origin})
        finally:
            wa.recent = real_recent
        check("an unexpected crash still answers 500 JSON", r.status_code == 500
              and r.json().get("code") == "INTERNAL_ERROR", f"HTTP {r.status_code}")
        check("an unexpected crash still carries CORS headers - the browser can read it",
              r.headers.get("access-control-allow-origin") == origin["Origin"])
    finally:
        meeting_service.run_transcript_extraction = real_extract
        db.rollback()
        db.query(TranscriptSegment).filter(TranscriptSegment.company_id == company.id).delete()
        db.query(Meeting).filter(Meeting.company_id == company.id).delete()
        db.query(User).filter(User.company_id == company.id).delete()
        db.query(Employee).filter(Employee.company_id == company.id).delete()
        db.query(Company).filter(Company.id == company.id).delete()
        db.commit()
        db.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("All WhatsApp import checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
