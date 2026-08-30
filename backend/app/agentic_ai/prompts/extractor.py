"""Transcript and meeting notes extraction prompt."""

from app.agentic_ai.prompts.base import render_base_prompt
from app.models.company import Company


def render_extractor_prompt(company: Company) -> str:
    """Render system prompt for transcript extraction."""
    base = render_base_prompt(company)

    return f"""{base}
Operational Task: Action Item & Commitment Extraction.
Analyze the provided meeting transcript, email, or notes to extract concrete commitments and tasks.

Rules for Extraction:
1. Extract only explicit commitments, decisions, and action items.
2. For each task, provide:
   - title: Clear, concise summary of the action required.
   - description: Additional context or requirements.
   - owner_employee_id: Match mentioned owner names against the employee list (or leave null if ambiguous/unassigned).
   - deadline: Extracted ISO-8601 deadline if mentioned (or null).
   - source_quote: Verbatim sentence or quote from the text demonstrating the commitment.
   - confidence: Confidence score between 0.0 and 1.0 based on how clear and unambiguous the commitment is.
3. Use the create_extracted_task tool for every extracted task.
"""
