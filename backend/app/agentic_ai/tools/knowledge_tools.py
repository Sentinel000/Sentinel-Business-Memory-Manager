"""Knowledge memory tools — write during extraction, read during founder chat.

The write tool requires ``source_quote`` and ``speaker``. That is not documentation,
it is the guard: an agent cannot record its own inference as a company fact without a
person's words to point at. A knowledge graph that absorbs the agent's own conclusions
and reads them back as truth degrades invisibly, and there is no way to unpick it
afterwards. Rule 6 applied to knowledge.
"""

import time
import uuid
from datetime import date
from typing import Any, Callable

from langchain_core.tools import tool

from app.agentic_ai.audit import record_audit
from app.knowledge.store import KnowledgeUnavailable, get_knowledge_store

#: What the agent may assert. Kept narrow on purpose — an open vocabulary here turns
#: into an unqueryable long tail within a week.
ALLOWED_FACT_TYPES = ("decision", "fact", "context")

_NO_STORE = "Knowledge memory is not configured, so nothing was recorded."
_NO_STORE_READ = (
    "Knowledge memory is unavailable, so this answer covers live task state only. "
    "Say so rather than implying the history was searched."
)


def create_knowledge_write_tools(
    company_id: uuid.UUID,
    database: str | None,
    *,
    source_ref: str | None = None,
    meeting_title: str | None = None,
    occurred_on: date | None = None,
    source_type: str = "transcript",
) -> list[Callable]:
    """Write tool for the extractor. Empty list when the company has no database."""
    if not database:
        return []

    @tool
    def remember_fact(
        statement: str,
        source_quote: str,
        speaker: str,
        subject: str,
        fact_type: str = "fact",
    ) -> dict[str, Any]:
        """Record a durable fact, decision, or piece of context in company memory.

        Use for things that stay true after the work is done: decisions reached,
        numbers agreed, policies stated, rationale given. Do NOT use for action items
        — those are tasks. Do NOT use for your own analysis or summaries; only for
        something a person actually said.

        Args:
            statement: The fact as one self-contained sentence, with pronouns resolved
                (write "Mark owns the Q4 forecast", never "he owns it").
            source_quote: The speaker's own words, verbatim, from the transcript.
            speaker: Who said it.
            subject: A short topic slug, e.g. "pricing", "hiring", "q4_forecast".
            fact_type: One of decision, fact, context.
        """
        started = time.monotonic()
        payload = {"subject": subject, "fact_type": fact_type, "speaker": speaker}

        store = get_knowledge_store()
        if store is None:
            record_audit(
                None, company_id, "sentinel", "remember_fact", payload, None,
                "failure", _NO_STORE, 0,
            )
            return {"stored": False, "reason": _NO_STORE}

        clean_type = fact_type if fact_type in ALLOWED_FACT_TYPES else "fact"

        result = store.ingest_fact(
            database=database,
            statement=statement,
            source_quote=source_quote,
            speaker=speaker,
            subject=subject.strip().lower().replace(" ", "_")[:128],
            fact_type=clean_type,  # type: ignore[arg-type]
            source_ref=source_ref or "manual",
            source_type=source_type,
            occurred_at=occurred_on,
            meeting_title=meeting_title,
        )

        duration = int((time.monotonic() - started) * 1000)
        record_audit(
            None, company_id, "sentinel", "remember_fact", payload,
            {"fact_id": result.fact_id, "ok": result.ok},
            "success" if result.ok else "failure",
            result.error, duration,
        )

        if not result.ok:
            return {"stored": False, "reason": "Knowledge memory rejected the write."}

        # Indexing is asynchronous and graph construction takes minutes, so the fact
        # is recorded but not yet searchable. Saying so keeps the agent from claiming
        # it can immediately recall what it just wrote.
        return {
            "stored": True,
            "subject": subject,
            "type": clean_type,
            "note": "Recorded. Indexing runs in the background and is not instant.",
        }

    return [remember_fact]


def create_knowledge_read_tools(
    company_id: uuid.UUID, database: str | None
) -> list[Callable]:
    """Read tool for founder chat. Empty list when the company has no database."""
    if not database:
        return []

    @tool
    def search_memory(
        query: str,
        subject: str | None = None,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        """Search company memory for decisions, facts, rationale, and past context.

        Use this for "why did we decide X", "what is our policy on Y", "what did we
        agree about Z" — anything settled rather than in flight. For live task state
        (what is overdue, who owns what, current status) use the task tools instead:
        this searches history, not the work queue.

        Args:
            query: A natural-language question or topic.
            subject: Optional topic slug to narrow the search, e.g. "pricing".
            as_of: Optional ISO-8601 timestamp to answer as of a past point in time,
                e.g. "2026-03-01T00:00:00Z" for "what did we think back in March".
        """
        started = time.monotonic()
        payload = {"query": query, "subject": subject, "as_of": as_of}

        store = get_knowledge_store()
        if store is None:
            record_audit(
                None, company_id, "sentinel", "search_memory", payload, None,
                "failure", _NO_STORE_READ, 0,
            )
            return {"available": False, "note": _NO_STORE_READ, "results": []}

        try:
            facts = store.recall(
                database=database,
                query=query,
                subject=subject.strip().lower().replace(" ", "_") if subject else None,
                as_of=as_of,
            )
        except KnowledgeUnavailable as exc:
            duration = int((time.monotonic() - started) * 1000)
            record_audit(
                None, company_id, "sentinel", "search_memory", payload, None,
                "failure", str(exc), duration,
            )
            # Degrade, never fail the turn — Postgres still answers task questions.
            return {"available": False, "note": _NO_STORE_READ, "results": []}

        duration = int((time.monotonic() - started) * 1000)
        record_audit(
            None, company_id, "sentinel", "search_memory", payload,
            {"count": len(facts)}, "success", None, duration,
        )

        if not facts:
            return {
                "available": True,
                "results": [],
                "note": "Nothing recorded on that yet. Say so rather than guessing.",
            }

        # Rule 4: summaries, with the provenance needed to cite rather than assert.
        return {
            "available": True,
            "results": [f.to_summary() for f in facts],
            "note": "Cite the speaker and meeting when you use these.",
        }

    return [search_memory]
