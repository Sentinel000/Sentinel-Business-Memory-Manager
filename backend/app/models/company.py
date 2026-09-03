"""Company — the tenant root. The only table without a company_id."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)

    #: Assistant identity and company context. Shape:
    #: {assistant_name, tone, company_context, glossary}
    #: assistant_name/tone shape Slack copy; company_context/glossary feed the
    #: extractor prompt. Founder-supplied free text — treated as data, length-capped
    #: at the Pydantic layer, and never able to relax the pending_approval gate.
    persona_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    #: How many days a task may sit untouched before the follow-up agent escalates.
    #: A real column, not a persona key: list_stale_tasks() reads it as an argument.
    #: Cron owns *when*, the agent owns *what* — timing is never a word the model
    #: interprets.
    escalation_after_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="3"
    )

    #: How many reminders a task gets before it stops being chased and is handed
    #: back to the founder. Deliberately low: with no push channel, a third nudge to
    #: someone who ignored two is delay, not persuasion — and every extra chase
    #: postpones the moment the founder learns the commitment is dead.
    max_chases: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")

    #: Minimum confidence score required to auto-approve an extracted task.
    #: Default is 1.0 (nothing auto-approves until tuned down).
    auto_approve_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )

    #: Slack bot token from OAuth (step 2). Not a login credential — an authorisation
    #: to act on this company's behalf.
    slack_bot_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_team_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    #: Tenant id in the knowledge layer (step 7).
    hydra_tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company {self.name!r}>"
