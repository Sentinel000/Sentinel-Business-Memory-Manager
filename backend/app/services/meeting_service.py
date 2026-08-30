"""Service layer for meeting recording, transcription, and task extraction."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentic_ai.agents.extractor import run_transcript_extraction
from app.exceptions import NotFoundError
from app.models.company import Company
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.services.asr_service import get_asr_client
from app.services.base import TenantService


class MeetingService(TenantService):
    """Coordinates meeting transcription, persistence, and Sentinel task extraction."""

    def __init__(self, db: Session, company: Company):
        # TenantService takes a company_id, not the Company row. The row is kept
        # separately because the extractor needs it for persona and threshold.
        super().__init__(db, company.id)
        self.company = company
        self.meetings = MeetingRepository(db, company.id)

    def list_meetings(self) -> list[Meeting]:
        """List recent meetings for tenant."""
        return list(self.meetings.list_recent())

    def get_meeting_or_404(self, meeting_id: uuid.UUID) -> Meeting:
        """Fetch meeting ensuring tenant isolation."""
        meeting = self.meetings.get(meeting_id)
        if not meeting:
            raise NotFoundError("Meeting not found.")
        return meeting

    def get_meeting_tasks(self, meeting: Meeting) -> list[Task]:
        """Fetch extracted tasks linked to this meeting."""
        # Match tasks by source_ref or meeting title
        source_ref_pattern = f"%{meeting.title}%"
        stmt = (
            select(Task)
            .where(
                Task.company_id == self.company.id,
                Task.source_ref.ilike(source_ref_pattern) | (Task.source_ref == str(meeting.id))
            )
            .order_by(Task.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def process_audio_meeting(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        title: str | None = None,
        actor: User | None = None,
    ) -> tuple[Meeting, list[dict[str, Any]]]:
        """Transcribe audio recording and extract structured tasks into approval queue."""
        resolved_title = title or (filename.rsplit(".", 1)[0] if filename else "Meeting Recording")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"

        meeting = self.meetings.create_meeting(
            title=resolved_title,
            audio_filename=filename,
            audio_format=ext,
            status=MeetingStatus.TRANSCRIBING,
        )

        try:
            # 1. Transcribe audio with Qwen ASR Flash
            asr_client = get_asr_client()
            asr_result = asr_client.transcribe(audio_bytes=audio_bytes, audio_format=ext)
            transcript_text = asr_result.get("text", "")
            duration = asr_result.get("duration_seconds", 0)

            meeting.raw_transcript = transcript_text
            meeting.duration_seconds = duration
            meeting.status = MeetingStatus.EXTRACTING
            self.db.commit()

            # Save segments if present
            for seg in asr_result.get("segments", []):
                self.meetings.add_segment(
                    meeting_id=meeting.id,
                    text=seg.get("text", ""),
                    start_time=seg.get("start_time", 0.0),
                    end_time=seg.get("end_time", 0.0),
                )

            extracted_tasks: list[dict[str, Any]] = []
            if transcript_text.strip():
                # 2. Sentinel Extractor Agent
                source_ref = f"Meeting: {meeting.title}"
                ext_res = run_transcript_extraction(
                    db=self.db,
                    company=self.company,
                    transcript_text=transcript_text,
                    source_ref=source_ref,
                )
                extracted_tasks = ext_res.get("tasks_extracted", [])

            meeting.status = MeetingStatus.COMPLETED
            self.db.commit()
            self.db.refresh(meeting)
            return meeting, extracted_tasks

        except Exception as e:
            self.db.rollback()
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = str(e)
            self.db.commit()
            raise

    def process_text_meeting(
        self,
        *,
        transcript: str,
        title: str,
        actor: User | None = None,
    ) -> tuple[Meeting, list[dict[str, Any]]]:
        """Process direct transcript text and extract structured tasks."""
        meeting = self.meetings.create_meeting(
            title=title,
            raw_transcript=transcript,
            audio_format="text",
            status=MeetingStatus.EXTRACTING,
        )

        try:
            # Sentinel Extractor Agent
            source_ref = f"Meeting: {meeting.title}"
            ext_res = run_transcript_extraction(
                db=self.db,
                company=self.company,
                transcript_text=transcript,
                source_ref=source_ref,
            )
            extracted_tasks = ext_res.get("tasks_extracted", [])

            meeting.status = MeetingStatus.COMPLETED
            self.db.commit()
            self.db.refresh(meeting)
            return meeting, extracted_tasks

        except Exception as e:
            self.db.rollback()
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = str(e)
            self.db.commit()
            raise
