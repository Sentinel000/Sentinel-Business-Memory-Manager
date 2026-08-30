"""Audit decorator for Sentinel tool calls (Rule 5)."""

import logging
import uuid
from typing import Any

from app.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def record_audit(
    _db: Any,
    company_id: uuid.UUID,
    agent: str,
    tool: str,
    tool_input: dict[str, Any] | None,
    result: dict[str, Any] | None,
    status: str = "success",
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Record an entry into the audit_log table using an isolated session."""
    session = SessionLocal()
    try:
        safe_input = _sanitize_payload(tool_input) if tool_input else None
        safe_result = _sanitize_payload(result) if result else None

        log_entry = AuditLog(
            company_id=company_id,
            agent=agent,
            tool=tool,
            input=safe_input,
            result=safe_result,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Failed to record audit log for {agent}:{tool}: {e}")
        session.rollback()
    finally:
        session.close()


def _sanitize_payload(data: Any) -> Any:
    """Remove sensitive fields from logged inputs and outputs."""
    if not isinstance(data, dict):
        return data
    sanitized = {}
    sensitive_keys = {"token", "password", "secret", "api_key", "bot_token", "slack_bot_token"}
    for k, v in data.items():
        if any(sens in k.lower() for sens in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_payload(v)
        else:
            sanitized[k] = v
    return sanitized
