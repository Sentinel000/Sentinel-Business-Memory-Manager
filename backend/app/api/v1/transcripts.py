"""Transcript upload and extraction API router."""

from fastapi import APIRouter
from app.agentic_ai.agents.extractor import run_transcript_extraction
from app.dependencies import DbSession, FounderUser
from app.schemas.chat import TranscriptRequest

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/transcripts")
def upload_transcript(
    payload: TranscriptRequest,
    current_founder: FounderUser,
    db: DbSession,
):
    """Upload meeting transcript/notes and extract actionable commitments."""
    result = run_transcript_extraction(
        db=db,
        company=current_founder.company,
        transcript_text=payload.transcript,
    )
    return result
