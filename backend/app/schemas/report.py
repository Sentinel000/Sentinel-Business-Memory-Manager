"""Founder briefing read models."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReportSection(BaseModel):
    key: str
    title: str
    #: Rendered when ``items`` is empty. "Nothing slipped" is a real answer.
    empty: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    #: Matches beyond the display cap, so the UI can say "and 7 more".
    hidden: int = 0


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    #: The day described.
    report_date: date
    #: When it was last rebuilt — distinct from ``report_date``, so the UI can say
    #: "Today · regenerated 2:14pm" and the founder knows exactly what they hold.
    generated_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    sections: list[ReportSection] = Field(default_factory=list)


class ReportSummary(BaseModel):
    """List-view row. The sections are the payload, so they are left out here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_date: date
    generated_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
