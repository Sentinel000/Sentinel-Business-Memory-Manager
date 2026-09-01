"""Meeting and Audio Transcription API router."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.dependencies import DbSession, FounderUser
from app.exceptions import ValidationError
from app.schemas.meeting import MeetingDetailRead, MeetingSummaryRead, MeetingTextCreate
from app.schemas.task import TaskSummary
from app.services.meeting_service import MeetingService

router = APIRouter(tags=["meetings"])


@router.post("/audio", response_model=MeetingDetailRead, status_code=status.HTTP_201_CREATED)
async def upload_meeting_audio(
    current_user: FounderUser,
    db: DbSession,
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> MeetingDetailRead:
    """Upload audio recording (WebM, WAV, MP3, M4A) for Qwen ASR transcription & task extraction."""
    if not file.filename:
        raise ValidationError("Uploaded file must have a filename.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise ValidationError("Uploaded audio file is empty.")

    svc = MeetingService(db, current_user.company)
    meeting, _ = svc.process_audio_meeting(
        audio_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type or "audio/webm",
        title=title,
        actor=current_user,
    )

    tasks = svc.get_meeting_tasks(meeting)
    detail = MeetingDetailRead.model_validate(meeting)
    detail.extracted_tasks = [TaskSummary.model_validate(t) for t in tasks]
    return detail


@router.post("/text", response_model=MeetingDetailRead, status_code=status.HTTP_201_CREATED)
def create_text_meeting(
    payload: MeetingTextCreate,
    current_user: FounderUser,
    db: DbSession,
) -> MeetingDetailRead:
    """Ingest transcript text or notes directly and extract action items."""
    svc = MeetingService(db, current_user.company)
    meeting, _ = svc.process_text_meeting(
        transcript=payload.transcript,
        title=payload.title,
        actor=current_user,
        recorded_at=payload.recorded_at,
    )

    tasks = svc.get_meeting_tasks(meeting)
    detail = MeetingDetailRead.model_validate(meeting)
    detail.extracted_tasks = [TaskSummary.model_validate(t) for t in tasks]
    return detail


@router.get("", response_model=list[MeetingSummaryRead])
def list_meetings(
    current_user: FounderUser,
    db: DbSession,
) -> list[MeetingSummaryRead]:
    """List all past meetings and transcription status for the tenant."""
    svc = MeetingService(db, current_user.company)
    meetings = svc.list_meetings()
    return [MeetingSummaryRead.model_validate(m) for m in meetings]


@router.get("/{meeting_id}", response_model=MeetingDetailRead)
def get_meeting(
    meeting_id: uuid.UUID,
    current_user: FounderUser,
    db: DbSession,
) -> MeetingDetailRead:
    """Retrieve full meeting details, transcript segments, and extracted tasks."""
    svc = MeetingService(db, current_user.company)
    meeting = svc.get_meeting_or_404(meeting_id)
    tasks = svc.get_meeting_tasks(meeting)
    detail = MeetingDetailRead.model_validate(meeting)
    detail.extracted_tasks = [TaskSummary.model_validate(t) for t in tasks]
    return detail
