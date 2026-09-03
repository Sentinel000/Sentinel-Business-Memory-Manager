"""Model package.

Every model is imported here so Base.metadata is complete when Alembic
autogenerates. A model that is not imported is a table Alembic will silently
propose dropping.
"""

from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.employee import Employee
from app.models.enums import ApprovalState, ReportedVia, TaskStatus, UserRole
from app.models.meeting import Meeting, MeetingStatus, TranscriptSegment
from app.models.report import Report
from app.models.status_update import StatusUpdate
from app.models.task import Task
from app.models.user import User

__all__ = [
    "Approval",
    "ApprovalState",
    "AuditLog",
    "Base",
    "Company",
    "Conversation",
    "Employee",
    "Meeting",
    "MeetingStatus",
    "Report",
    "ReportedVia",
    "StatusUpdate",
    "Task",
    "TaskStatus",
    "TenantMixin",
    "TimestampMixin",
    "TranscriptSegment",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserRole",
]
