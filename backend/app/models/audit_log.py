"""AuditLog — one row per tool call. Rule 5.

Two jobs: the 3am debugging tool, and the answer to "how do you know the AI did the
right thing?" Append-only; nothing updates a row here.
"""

from typing import Any

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_company_created", "company_id", "created_at"),)

    #: extractor | followup | chat, or null for a human action.
    agent: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tool: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    #: Arguments and result. Never log credentials or personal data into these —
    #: see docs/rules/security.md. Callers are responsible for redaction.
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.agent}:{self.tool} {self.status}>"
