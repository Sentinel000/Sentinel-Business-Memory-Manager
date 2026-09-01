"""Turning a LangGraph message list into the chat API's wire shape.

Shared by the live chat turn and by thread rehydration so a reloaded conversation
renders identically to the one the founder just typed — including its tool cards.
"""

import json
from typing import Any

from app.agentic_ai.audit import _sanitize_payload

#: Rule 4: tools return summaries by default. A full tool payload in every chat
#: response is the same context blowout on the wire that it is in the agent loop,
#: so the transcript carries a preview and the UI marks it truncated.
MAX_TOOL_RESULT_CHARS = 600


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text, False
    return text[:MAX_TOOL_RESULT_CHARS].rstrip() + "…", True


def slice_current_turn(messages: list[Any]) -> list[Any]:
    """The messages produced since the founder's most recent question.

    A thread runs on a checkpointer, so an agent invocation returns the whole
    accumulated conversation. Shipping all of it back on every turn made a third
    reply claim it consulted every tool the thread had ever called; this narrows
    the live response to the delta the founder just caused.
    """
    last_human = -1
    for i, msg in enumerate(messages):
        if getattr(msg, "type", "") == "human":
            last_human = i
    return messages[last_human:] if last_human >= 0 else messages


def _parse_payload(raw: str) -> Any:
    """The tool's return value as structured data, or None when it is not JSON."""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Fold a raw message list into user/agent turns with their tool executions.

    Tool calls and their results are paired by ``tool_call_id`` and attached to the
    assistant turn they produced, rather than surfacing as their own chat bubbles.
    """
    turns: list[dict[str, Any]] = []
    # tool_call_id -> execution being assembled, awaiting its ToolMessage result.
    pending: dict[str, dict[str, Any]] = {}
    completed: list[dict[str, Any]] = []

    for msg in messages:
        msg_type = getattr(msg, "type", "")

        if msg_type == "human":
            turns.append({"role": "user", "content": str(msg.content), "tool_executions": []})
            continue

        if msg_type == "tool":
            call_id = getattr(msg, "tool_call_id", "") or ""
            raw = str(msg.content)
            result, truncated = _truncate(raw)
            execution = pending.pop(call_id, None) or {
                "id": call_id,
                "tool": getattr(msg, "name", "tool"),
                "args": {},
            }
            execution["result"] = result
            execution["truncated"] = truncated
            # Parse the untruncated content: `result` is cut mid-string and is not
            # valid JSON. `kind` is set by the tool on its success path only, so an
            # error return has none and the UI falls back to the raw view.
            parsed = _parse_payload(raw)
            execution["data"] = parsed
            execution["kind"] = parsed.get("kind") if isinstance(parsed, dict) else None
            # LangChain marks a failed tool call on the message itself.
            execution["ok"] = getattr(msg, "status", "success") != "error"
            completed.append(execution)
            continue

        if msg_type == "ai":
            for call in getattr(msg, "tool_calls", None) or []:
                call_id = call.get("id") or ""
                pending[call_id] = {
                    "id": call_id,
                    "tool": call.get("name", "tool"),
                    # Args can carry emails and ids — run them through the same
                    # redaction the audit log uses before they reach a browser.
                    "args": _sanitize_payload(call.get("args") or {}),
                }

            content = str(msg.content or "")
            if content.strip():
                turns.append(
                    {"role": "agent", "content": content, "tool_executions": completed}
                )
                completed = []

    # Tool calls that produced no closing assistant message still deserve to render.
    if completed:
        turns.append({"role": "agent", "content": "", "tool_executions": completed})

    return turns


def extract_tool_executions(messages: list[Any]) -> list[dict[str, Any]]:
    """Every tool execution across a message list, newest turn last."""
    return [ex for turn in serialize_messages(messages) for ex in turn["tool_executions"]]
