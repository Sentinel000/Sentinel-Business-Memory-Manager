"""Cron follow-up and digest system prompt."""

from app.agentic_ai.prompts.base import render_base_prompt
from app.models.company import Company


def render_cron_prompt(company: Company) -> str:
    """Render system prompt for the daily Cron follow-up execution."""
    base = render_base_prompt(company)
    escalation_window = company.escalation_after_days

    return f"""{base}
Operational Task: Daily Follow-up and Morning Digest.
You are running automatically on schedule to ensure commitments are kept across {company.name}.

Instructions:
1. Inspect all open and overdue tasks across the company.
2. If a task has been inactive and untouched for >= {escalation_window} days:
   - Escalate to the owner's manager using the escalate_task tool.
3. If an open task is nearing its deadline or needs a gentle status check:
   - Send a reminder to the owner using the send_reminder tool.
4. Produce a crisp executive digest summarizing:
   - What was accomplished yesterday
   - What is currently blocked or escalated
   - Key priorities due today
"""
