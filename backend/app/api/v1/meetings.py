"""Meeting and Audio Transcription API router."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.dependencies import DbSession, FounderUser
from app.exceptions import ExtractionFailedError, SentinelError, ValidationError
from app.schemas.meeting import MeetingDetailRead, MeetingSummaryRead, MeetingTextCreate
from app.schemas.task import TaskSummary
from app.services import whatsapp_import
from app.services.meeting_service import MeetingService

router = APIRouter(tags=["meetings"])


def _extraction_failed(exc: Exception) -> ExtractionFailedError:
    """What the founder sees when the model call fails mid-extraction.

    The meeting row is already saved with status failed, so the message says so.
    The underlying error is logged by the service, never echoed: provider errors can
    quote request details.
    """
    logging.getLogger(__name__).warning("Extraction failed: %s", type(exc).__name__)
    return ExtractionFailedError(
        "The upload was saved, but Sentinel could not reach the AI model to extract "
        "commitments. Try again in a minute."
    )


@router.post("/audio", response_model=MeetingDetailRead, status_code=status.HTTP_201_CREATED)
def upload_meeting_audio(
    current_user: FounderUser,
    db: DbSession,
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> MeetingDetailRead:
    """Upload audio recording (WebM, WAV, MP3, M4A) for Qwen ASR transcription & task extraction.

    A plain ``def`` on purpose. Transcription and extraction are blocking calls that
    can run for a minute; inside ``async def`` they ran on the event loop and froze
    every other request from every tenant until they finished. FastAPI runs a plain
    ``def`` in its threadpool instead.
    """
    if not file.filename:
        raise ValidationError("Uploaded file must have a filename.")

    file_bytes = file.file.read()
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


@router.post("/whatsapp", response_model=MeetingDetailRead, status_code=status.HTTP_201_CREATED)
def import_whatsapp_chat(
    current_user: FounderUser,
    db: DbSession,
    file: UploadFile = File(...),
    days: int = Form(7, ge=1, le=90),
    title: str | None = Form(None),
) -> MeetingDetailRead:
    """Extract commitments from a WhatsApp "Export chat" file (.txt, or the iPhone .zip).

    No WhatsApp API is involved - the founder exports the chat themselves. Only the
    last ``days`` of the conversation are read, measured back from its newest
    message, because a group export carries its whole history.
    """
    try:
        text = whatsapp_import.read_export(
            file.file.read(whatsapp_import.MAX_EXPORT_BYTES + 1), file.filename
        )
        chat = whatsapp_import.parse_export(text)
    except whatsapp_import.NotAWhatsAppExport as exc:
        raise ValidationError(str(exc)) from None

    window = whatsapp_import.recent(chat.messages, days)
    if not window:
        raise ValidationError(f"No messages from the last {days} days were found in that chat.")
    if len(window) > whatsapp_import.MAX_MESSAGES:
        window = window[-whatsapp_import.MAX_MESSAGES:]

    group = whatsapp_import.group_name(file.filename) or "WhatsApp group"
    svc = MeetingService(db, current_user.company)
    try:
        meeting, _ = svc.process_text_meeting(
            transcript=whatsapp_import.render_transcript(window),
            title=title or f"WhatsApp: {group}",
            actor=current_user,
            recorded_at=window[-1].at,
            source_ref=f"WhatsApp: {group}",
            source_kind="whatsapp",
            audio_filename=file.filename,
        )
    except SentinelError:
        raise
    except Exception as exc:
        raise _extraction_failed(exc) from exc

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
    try:
        meeting, _ = svc.process_text_meeting(
            transcript=payload.transcript,
            title=payload.title,
            actor=current_user,
            recorded_at=payload.recorded_at,
        )
    except SentinelError:
        raise
    except Exception as exc:
        raise _extraction_failed(exc) from exc

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


@router.get("/{meeting_id}/delete-preview")
def preview_meeting_delete(
    meeting_id: uuid.UUID,
    current_user: FounderUser,
    db: DbSession,
) -> dict:
    """What deleting this meeting would remove. Changes nothing.

    `fact_count` is null when the knowledge store could not be reached — the UI
    must say "unknown" rather than "0", so the founder never confirms a permanent
    delete against a count that was really a failed lookup.
    """
    svc = MeetingService(db, current_user.company)
    return svc.preview_delete(svc.get_meeting_or_404(meeting_id))


@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: uuid.UUID,
    current_user: FounderUser,
    db: DbSession,
) -> dict:
    """Permanently delete a meeting and every fact extracted from it.

    Irreversible, and deliberately not a soft delete: the founder asked for the
    knowledge to go. Extracted tasks are kept — they may be live commitments — so
    their source citation is left dangling rather than silently removing work.
    """
    svc = MeetingService(db, current_user.company)
    return svc.delete_meeting(svc.get_meeting_or_404(meeting_id))
