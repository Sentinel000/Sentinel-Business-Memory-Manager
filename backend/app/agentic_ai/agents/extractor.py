"""Transcript and meeting notes extraction agent runner."""

from datetime import UTC, date, datetime
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentic_ai.factory import build_sentinel
from app.knowledge.provisioning import ensure_knowledge_database
from app.models.company import Company
from app.models.task import Task
from app.schemas.task import TaskSummary


def run_transcript_extraction(
    db: Session,
    company: Company,
    transcript_text: str,
    source_ref: str | None = None,
    meeting_title: str | None = None,
    occurred_on: date | None = None,
) -> dict[str, Any]:
    """Process a raw transcript or meeting recording, extracting structured action items.

    A transcript produces tasks (Postgres) and knowledge (HydraDB). The knowledge
    database is provisioned here rather than only at signup, so companies created
    before knowledge memory existed pick it up on their next meeting.
    """
    ensure_knowledge_database(db, company)

    agent = build_sentinel(
        db,
        company,
        entry="transcript",
        source_ref=source_ref,
        meeting_title=meeting_title,
        occurred_on=occurred_on,
    )

    # Bound the result query to this run. Filtering on created_by_agent alone returns
    # tasks from every previous extraction, so a second meeting would report the
    # first meeting's tasks as its own.
    started_at = datetime.now(UTC)

    prompt = (
        f"Please extract all action items and commitments from the following transcript.\n"
        f"For every task found, call create_extracted_task with verbatim source_quote and confidence score.\n\n"
        f"--- TRANSCRIPT START ---\n"
        f"{transcript_text}\n"
        f"--- TRANSCRIPT END ---"
    )

    response = agent.invoke({"messages": [HumanMessage(content=prompt)]})

    # Fetch tasks created during this run
    recent_tasks = db.execute(
        select(Task)
        .where(
            Task.company_id == company.id,
            Task.created_by_agent == "extractor",
            Task.created_at >= started_at,
        )
        .order_by(Task.created_at.desc())
    ).scalars().all()

    task_summaries = []
    for t in recent_tasks:
        s = TaskSummary.model_validate(t)
        if t.owner:
            s.owner_name = t.owner.name
        task_summaries.append(s.model_dump(mode="json"))

    messages = response.get("messages", [])
    summary_text = messages[-1].content if messages else "Extraction complete."

    return {
        "summary": summary_text,
        "tasks_extracted": task_summaries,
    }
