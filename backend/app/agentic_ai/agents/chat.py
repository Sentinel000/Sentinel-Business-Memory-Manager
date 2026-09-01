"""Chat agent execution runner."""

import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentic_ai.factory import build_sentinel
from app.agentic_ai.serialization import extract_tool_executions, slice_current_turn
from app.exceptions import ForbiddenError, NotFoundError
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.user import User


def run_chat_turn(
    db: Session,
    company: Company,
    actor: User,
    message: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Execute a single conversational turn with Sentinel."""
    # Resolve or create conversation thread
    if conversation_id:
        try:
            cid = uuid.UUID(conversation_id)
        except ValueError:
            raise NotFoundError("Conversation not found.")

        conv = db.execute(
            select(Conversation).where(Conversation.id == cid)
        ).scalar_one_or_none()

        if not conv:
            raise NotFoundError("Conversation not found.")
        # Strict tenant and user isolation (Rule 1 & Rule 6)
        if conv.company_id != company.id or conv.user_id != actor.id:
            raise ForbiddenError("Access to conversation thread forbidden.")
    else:
        # Create initial conversation title from message snippet
        title_snippet = (message[:40] + "...") if len(message) > 40 else message
        conv = Conversation(
            company_id=company.id,
            user_id=actor.id,
            title=title_snippet,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    agent = build_sentinel(db, company, actor=actor, entry="chat")
    config = {"configurable": {"thread_id": str(conv.id)}}

    response = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    # Extract final assistant reply
    messages = response.get("messages", [])
    reply_content = ""
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "ai" and msg.content:
            reply_content = msg.content
            break

    if not reply_content and messages:
        reply_content = str(messages[-1].content)

    return {
        "reply": reply_content,
        "conversation_id": str(conv.id),
        "title": conv.title,
        # What *this* reply was derived from, so the founder can verify it rather
        # than trust it. Sliced to the current turn: `messages` is the whole
        # checkpointed thread, and returning all of it made every reply claim
        # credit for tools called earlier in the conversation.
        "tool_executions": extract_tool_executions(slice_current_turn(messages)),
    }
