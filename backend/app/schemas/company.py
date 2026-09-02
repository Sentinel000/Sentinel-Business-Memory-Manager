"""Company and persona contracts."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

#: company_context is founder-supplied free text that ends up inside a system prompt.
#: Capping it is what keeps it a bounded piece of data rather than an open channel into
#: the model. It must never be able to relax the pending_approval gate — the prompt
#: treats it as background, and approval is enforced by the schema regardless.
MAX_COMPANY_CONTEXT = 4_000


class PersonaConfig(BaseModel):
    """How the assistant presents itself, and what it knows about the company.

    assistant_name and tone shape the Slack DM copy. company_context and glossary go
    into the extractor prompt — they are what resolve "Mark" to a person and "ACV" to
    a meaning.
    """

    assistant_name: str = Field(default="Sentinel", max_length=64)
    tone: str = Field(default="direct", max_length=64)
    company_context: str = Field(default="", max_length=MAX_COMPANY_CONTEXT)
    glossary: dict[str, str] = Field(default_factory=dict)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None = None
    persona_config: PersonaConfig
    #: Days of silence tolerated before a reminder. Also the gap between reminders.
    escalation_after_days: int
    #: Reminders sent before a task stops being chased and is handed to the founder.
    max_chases: int = 2
    #: Confidence at or above which an extracted task skips the approval queue.
    auto_approve_threshold: float = 1.0
    #: Never the token itself. Whether Slack is connected is all the dashboard needs,
    #: and a bot token in a JSON response is a credential in a browser's memory.
    slack_connected: bool = False
    slack_team_id: str | None = None
    knowledge_connected: bool = False


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, min_length=1, max_length=200)
    persona_config: PersonaConfig | None = None
    #: How long a task may sit untouched before escalation. A real number the
    #: follow-up tool reads as an argument, never a word the model interprets.
    escalation_after_days: int | None = Field(default=None, ge=1, le=30)
    #: Capped at 5. A longer ladder does not persuade anyone — it only delays the
    #: moment the founder learns a commitment is dead, and fills the briefing with
    #: tasks nobody will action.
    max_chases: int | None = Field(default=None, ge=1, le=5)
    #: 1.0 means nothing auto-approves. Below 0.5 the founder is effectively no
    #: longer reviewing, so the floor is deliberate rather than arbitrary.
    auto_approve_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
