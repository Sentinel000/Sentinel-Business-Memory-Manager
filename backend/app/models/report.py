"""Founder briefing — a persisted snapshot of the commitment ledger.

Replaces the cron digest, which was generated daily and discarded. Generated on
demand rather than on a schedule: the founder reads it when they sit down, and a
report built at 08:00 is stale by the time anyone opens it.

Every figure in it is computed in SQL. Nothing here is model output — a briefing
that miscounts is worse than no briefing.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.company import Company


class Report(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        # One row per company per day. Regenerating updates it in place, so a
        # founder who clicks twice gets one report and not two versions of the same
        # morning with no way to tell which is current.
        UniqueConstraint("company_id", "report_date", name="uq_reports_company_date"),
    )

    #: The day being described.
    report_date: Mapped[Any] = mapped_column(Date, nullable=False, index=True)

    #: When it was last rebuilt. Distinct from ``report_date`` so the UI can say
    #: "Today · regenerated 2:14pm" and the founder knows exactly what they hold.
    generated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    #: The four rendered sections, each a capped list of items. JSONB because the
    #: shape is presentational and will change faster than a migration cadence
    #: allows — nothing queries into it, it is read whole and rendered.
    sections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    #: Headline figures, kept out of ``sections`` because they are the one part a
    #: founder may want to trend over time.
    counts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    company: Mapped["Company"] = relationship()

    def __repr__(self) -> str:
        return f"<Report {self.report_date} company={self.company_id}>"
