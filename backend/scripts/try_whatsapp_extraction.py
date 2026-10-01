"""Run the real extractor over a WhatsApp export and show what it finds.

    python -m scripts.try_whatsapp_extraction                      # the bundled demo chat
    python -m scripts.try_whatsapp_extraction path/to/chat.txt --days 14

Needs QWEN_API_KEY. Works in a throwaway company that is deleted afterwards, with the
knowledge layer switched off for the run so nothing is written to HydraDB. Use it to
check extraction quality - Roman Urdu especially - before relying on it in a demo.
"""

import argparse
import sys
import uuid
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Company, Employee
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.meeting import Meeting, TranscriptSegment
from app.models.status_update import StatusUpdate
from app.models.task import Task
from app.services import whatsapp_import as wa
from app.services.meeting_service import MeetingService

DEMO = Path(__file__).resolve().parents[2] / "docs" / "demo" / "WhatsApp Chat with Delivery Team.txt"

#: What a good run over the demo chat should find. Dates follow from when each
#: message was sent (the chat runs Wed 23 Sep to Tue 29 Sep 2026).
EXPECTED = """
  Hamza   unblock the Meridian dataset          Thu 24 Sep  ("Kal tak" on Wed 23)
  Bilal   finish the evaluation harness         Wed 30 Sep  (moved from Mon 28)
  Bilal   send Sana the latency/accuracy numbers Fri 25 Sep
  Hamza   update the pricing page               by 30 Sep
  Sana    draft renewal talking points          no deadline
  Sana    publish the case study after legal    30 Sep
  Hamza   follow up with Meridian again         Tue 29 Sep  ("aaj hi")
  Decision: from 1 October new retainers start at 12,000 a month; no hourly quotes.
"""

DEMO_TEAM = ["Ayesha Khan", "Bilal Ahmed", "Hamza Sheikh", "Sana Malik"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEMO))
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    if not settings.qwen_api_key:
        print("QWEN_API_KEY is not set. This script calls the real model.")
        return 2

    path = Path(args.path)
    chat = wa.parse_export(wa.read_export(path.read_bytes(), path.name))
    window = wa.recent(chat.messages, args.days)
    group = wa.group_name(path.name) or "WhatsApp group"
    senders = sorted({m.sender for m in window})
    print(f"\n{len(window)} messages from {len(senders)} people in '{group}' "
          f"({window[0].at:%d %b} to {window[-1].at:%d %b}).")

    # Nothing from a trial run should reach long-term memory.
    settings.hydra_db_api_key = ""

    db = SessionLocal()
    tag = uuid.uuid4().hex[:6]
    company = Company(name=f"extraction-trial-{tag}", escalation_after_days=3, max_chases=2)
    db.add(company)
    db.flush()
    # The people in the chat become the roster, so owners can be matched to them.
    for name in sorted(set(senders) | (set(DEMO_TEAM) if path == DEMO else set())):
        db.add(Employee(company_id=company.id, name=name))
    db.commit()

    try:
        meeting, _ = MeetingService(db, company).process_text_meeting(
            transcript=wa.render_transcript(window),
            title=f"WhatsApp: {group}",
            recorded_at=window[-1].at,
            source_ref=f"WhatsApp: {group}",
            source_kind="whatsapp",
        )
        tasks = db.query(Task).filter(Task.company_id == company.id).order_by(Task.created_at).all()
        names = {e.id: e.name for e in db.query(Employee).filter(Employee.company_id == company.id)}

        print(f"\nExtracted {len(tasks)} commitment(s):\n")
        for t in tasks:
            owner = names.get(t.owner_employee_id, "(no owner)")
            due = f"{t.deadline:%a %d %b}" if t.deadline else "no deadline"
            conf = f"{t.confidence:.0%}" if t.confidence is not None else "  ?"
            print(f"  {owner:<14} {t.title}")
            print(f"  {'':<14} {due}  |  confidence {conf}")
            print(f"  {'':<14} \"{t.source_quote}\"\n")

        if path == DEMO:
            print("What a good run should roughly find:" + EXPECTED)
            print("Look for: owners right, dates resolved against the day each message was")
            print("sent, quotes left in Roman Urdu, titles in English.")
    finally:
        db.rollback()
        task_ids = [t.id for t in db.query(Task.id).filter(Task.company_id == company.id)]
        db.query(StatusUpdate).filter(StatusUpdate.company_id == company.id).delete()
        db.query(Approval).filter(Approval.company_id == company.id).delete()
        db.query(AuditLog).filter(AuditLog.company_id == company.id).delete()
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        db.query(TranscriptSegment).filter(TranscriptSegment.company_id == company.id).delete()
        db.query(Meeting).filter(Meeting.company_id == company.id).delete()
        db.query(Employee).filter(Employee.company_id == company.id).delete()
        db.query(Company).filter(Company.id == company.id).delete()
        db.commit()
        db.close()
        print("(Trial company deleted.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
