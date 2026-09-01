"""Chat API router."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentic_ai.agents.chat import run_chat_turn
from app.agentic_ai.checkpointer import get_checkpointer
from app.dependencies import CurrentUser, DbSession
from app.exceptions import ForbiddenError, NotFoundError
from app.models.conversation import Conversation
from app.models.user import User
from app.agentic_ai.serialization import serialize_messages
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationRead,
)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ChatResponse:
    """Send a message to Sentinel and receive a reply."""
    result = run_chat_turn(
        db=db,
        company=current_user.company,
        actor=current_user,
        message=payload.message,
        conversation_id=payload.conversation_id,
    )
    return ChatResponse(**result)


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(
    current_user: CurrentUser,
    db: DbSession,
) -> list[ConversationRead]:
    """List conversation threads belonging to the current user."""
    threads = db.execute(
        select(Conversation)
        .where(Conversation.company_id == current_user.company_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    ).scalars().all()
    return [ConversationRead.model_validate(t) for t in threads]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationDetail:
    """Retrieve details and messages of a conversation thread."""
    conv = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    ).scalar_one_or_none()

    if not conv or conv.company_id != current_user.company_id or conv.user_id != current_user.id:
        raise NotFoundError("Conversation not found.")

    # Retrieve messages from checkpointer
    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": str(conv.id)}}
    checkpoint = checkpointer.get(config)

    raw_msgs = []
    if checkpoint and "channel_values" in checkpoint:
        raw_msgs = checkpoint["channel_values"].get("messages", [])

    # Serialized the same way as a live turn, so a reloaded thread renders
    # identically — tool cards included — instead of as raw message types.
    return ConversationDetail(
        conversation=ConversationRead.model_validate(conv),
        messages=serialize_messages(raw_msgs),
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Remove one of the current user's threads.

    Scoped to the owner: a thread from another user or tenant reads as absent
    rather than as forbidden, so ids cannot be probed.
    """
    conv = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    ).scalar_one_or_none()

    if not conv or conv.company_id != current_user.company_id or conv.user_id != current_user.id:
        raise NotFoundError("Conversation not found.")

    db.delete(conv)
    db.commit()
