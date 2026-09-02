"""Pydantic schemas for meetings and transcripts."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.meeting import MeetingStatus
from app.schemas.task import TaskSummary


class TranscriptSegmentRead(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    speaker_label: str
    speaker_employee_id: uuid.UUID | None = None
    start_time: float
    end_time: float
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingSummaryRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    recorded_at: datetime
    duration_seconds: int | None = None
    audio_format: str | None = None
    status: MeetingStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingDetailRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    recorded_at: datetime
    duration_seconds: int | None = None
    audio_filename: str | None = None
    audio_format: str | None = None
    raw_transcript: str | None = None
    status: MeetingStatus
    error_message: str | None = None
    segments: list[TranscriptSegmentRead] = []
    extracted_tasks: list[TaskSummary] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingTextCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the meeting or transcript")
    transcript: str = Field(..., min_length=5, description="Verbatim transcript or meeting notes")
    #: When the meeting actually happened, which is not always when it was uploaded.
    #: Every fact extracted carries this date, and temporal recall reasons over it —
    #: so a back-dated transcript stamped with the upload date answers "what did we
    #: decide in March" wrongly. Defaults to now when omitted.
    recorded_at: datetime | None = Field(
        default=None, description="When the meeting took place (ISO-8601). Defaults to now."
    )
