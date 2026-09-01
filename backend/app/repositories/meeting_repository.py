"""Repository for tenant-scoped meeting persistence."""

import uuid
from datetime import datetime
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus, TranscriptSegment
from app.repositories.base import TenantScopedRepository


class MeetingRepository(TenantScopedRepository[Meeting]):
    model = Meeting

    def __init__(self, db: Session, company_id: uuid.UUID):
        super().__init__(db, company_id)

    def list_recent(self, limit: int = 50) -> Sequence[Meeting]:
        """List meetings ordered by recorded_at descending."""
        stmt = (
            select(Meeting)
            .where(Meeting.company_id == self.company_id)
            .order_by(Meeting.recorded_at.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def create_meeting(
        self,
        *,
        title: str,
        audio_filename: str | None = None,
        audio_format: str | None = None,
        raw_transcript: str | None = None,
        status: MeetingStatus = MeetingStatus.PENDING,
        duration_seconds: int | None = None,
        recorded_at: datetime | None = None,
    ) -> Meeting:
        """Create a new tenant meeting record."""
        meeting = Meeting(
            company_id=self.company_id,
            title=title,
            audio_filename=audio_filename,
            audio_format=audio_format,
            raw_transcript=raw_transcript,
            status=status,
            duration_seconds=duration_seconds,
        )
        # Left to the column default when the caller does not know the real date.
        if recorded_at is not None:
            meeting.recorded_at = recorded_at
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting

    def add_segment(
        self,
        meeting_id: uuid.UUID,
        *,
        text: str,
        start_time: float = 0.0,
        end_time: float = 0.0,
        speaker_label: str = "Speaker 1",
        speaker_employee_id: uuid.UUID | None = None,
    ) -> TranscriptSegment:
        """Add a transcript segment to a meeting."""
        seg = TranscriptSegment(
            company_id=self.company_id,
            meeting_id=meeting_id,
            text=text,
            start_time=start_time,
            end_time=end_time,
            speaker_label=speaker_label,
            speaker_employee_id=speaker_employee_id,
        )
        self.db.add(seg)
        self.db.commit()
        self.db.refresh(seg)
        return seg
