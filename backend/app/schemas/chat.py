"""Schemas for Chat and Conversation threads."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolExecution(BaseModel):
    """One tool call the agent made, with its (truncated) result.

    Surfaced so the founder can see what the answer was actually derived from —
    the same audit trail the system records, rendered in the chat.
    """

    id: str = ""
    tool: str
    args: dict = {}
    result: str = ""
    ok: bool = True
    truncated: bool = False
    #: Set by the tool itself on its success path, e.g. "task_list", "task_created".
    #: The frontend keys its renderer on this; an error return carries no kind and
    #: falls back to the raw JSON view.
    kind: str | None = None
    #: The untruncated parsed payload. `result` is capped for the agent's context
    #: budget (Rule 4); the browser has no such constraint and renders from here.
    data: Any = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    title: str
    tool_executions: list[ToolExecution] = []


class ConversationTurn(BaseModel):
    """A rehydrated message, shaped exactly like a live turn."""

    role: str
    content: str
    tool_executions: list[ToolExecution] = []


class ConversationDetail(BaseModel):
    conversation: "ConversationRead"
    messages: list[ConversationTurn] = []


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class TranscriptRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
