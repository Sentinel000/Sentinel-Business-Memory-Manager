"""Transcript and meeting notes extraction prompt."""

from datetime import UTC, date, datetime
from typing import Literal

from app.agentic_ai.prompts.base import render_base_prompt
from app.models.company import Company

SourceKind = Literal["meeting", "whatsapp"]


def _dates_section(occurred_on: date | None, source_kind: SourceKind) -> str:
    """Anchor relative deadlines. Without this the model is never told the date, so
    "by Friday" became a guessed ISO date - and deadlines drive the whole chase."""
    today = datetime.now(UTC).date()
    lines = [f"Today is {today:%A} {today.day} {today:%B %Y}."]
    if source_kind == "whatsapp":
        lines.append(
            "Every line starts with the date and time that message was sent. Resolve a "
            "relative deadline against the date of the message it appears in."
        )
    elif occurred_on is not None:
        lines.append(
            f"This conversation took place on {occurred_on:%A} {occurred_on.day} "
            f"{occurred_on:%B %Y}. Resolve relative deadlines against that date, not today."
        )
    else:
        lines.append("Resolve relative deadlines against today.")
    lines.append(
        "Write deadlines as ISO-8601 dates. If nobody stated a deadline, leave it null "
        "rather than inventing one."
    )
    return "\n".join(lines)


_LANGUAGE = """People may write in English, Urdu, Roman Urdu (Urdu in English letters), or a
mix of them in one sentence. Understand all of them. Write titles and descriptions in
clear English. Copy source_quote exactly as it was written - same language, same
spelling, never translated or tidied - because the founder sees it as the proof."""

_WHATSAPP = """This is a WhatsApp group chat. Each line is "[date time] Sender: message", and
the sender is exactly who said it. A commitment can be taken on by the sender ("I'll
send it tonight") or given to someone by name ("Bilal, send it by Friday"); either way
the owner is the person who will do the work. Skip greetings, jokes, links and bare
acknowledgements ("ok", "done", a thumbs up) unless they accept a specific task."""


def render_extractor_prompt(
    company: Company,
    *,
    occurred_on: date | None = None,
    source_kind: SourceKind = "meeting",
) -> str:
    """Render system prompt for transcript extraction."""
    base = render_base_prompt(company)
    source_note = f"\n{_WHATSAPP}\n" if source_kind == "whatsapp" else ""

    return f"""{base}
Dates:
{_dates_section(occurred_on, source_kind)}

Language:
{_LANGUAGE}
{source_note}
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

Operational Task 2: Knowledge Capture.
A transcript yields two different things. Commitments become tasks. Knowledge becomes
memory. Most meetings produce both, and one sentence is often both at once:
"We're going with $49 and Mark updates the pricing page by Friday" is one decision
(pricing is $49) plus one task (Mark, pricing page, Friday). Record both.

Call remember_fact for anything that stays true after the work is done:
- Decisions reached, and the reasoning behind them (fact_type="decision")
- Numbers, policies, or definitions agreed (fact_type="fact")
- Background that explains how the company operates (fact_type="context")

Do NOT call remember_fact for:
- Action items or commitments — those are tasks, and they expire.
- Your own analysis, summaries, or conclusions. Only record what a person actually
  said. If you cannot quote them, there is nothing to record.
- Small talk, scheduling chatter, or anything nobody would ask about in six months.

When calling remember_fact:
- statement: one self-contained sentence with pronouns resolved. Write "Mark owns the
  Q4 forecast", never "he owns it" — the sentence is read later with no transcript
  around it.
- source_quote: the speaker's own words, verbatim.
- speaker: who said it.
- subject: a short reusable topic slug ("pricing", "hiring", "q4_forecast"), so later
  statements about the same topic group together.
"""
