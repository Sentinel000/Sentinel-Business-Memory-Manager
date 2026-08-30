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
    escalation_after_days: int
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
