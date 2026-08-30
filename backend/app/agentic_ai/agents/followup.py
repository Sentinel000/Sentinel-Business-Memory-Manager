"""Cron daily follow-up and digest runner."""

from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.agentic_ai.factory import build_sentinel
from app.models.company import Company


def run_cron_followup(db: Session, company: Company) -> dict[str, Any]:
    """Execute the automated daily chasing routine for open commitments."""
    agent = build_sentinel(db, company, entry="cron")

    prompt = (
        f"Execute the daily follow-up cycle for {company.name}.\n"
        f"1. Query open and in-progress tasks.\n"
        f"2. Send reminders for tasks needing follow-up.\n"
        f"3. Escalate any task that has been inactive for >= {company.escalation_after_days} days.\n"
        f"4. Provide a clear morning executive digest summarizing task statuses and escalations."
    )

    response = agent.invoke({"messages": [HumanMessage(content=prompt)]})

    messages = response.get("messages", [])
    digest_content = messages[-1].content if messages else "Follow-up cycle completed."

    return {
        "status": "completed",
        "company": company.name,
        "digest": digest_content,
    }
