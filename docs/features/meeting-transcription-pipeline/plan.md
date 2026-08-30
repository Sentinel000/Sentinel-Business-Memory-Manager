# Meeting Audio Transcription & Action Item Extraction Pipeline

## Context & Problem Statement
Founders and executive teams frequently hold meetings (via Zoom, Google Meet, in-person recordings, or dashboard live recording) where critical commitments and action items are made. Today, capturing these action items requires manual transcription, hours of note-taking, or relying on black-box tools that output unverified bullet points without accountability.

Sentinel closes this loop:
1. **Live & File Capture**: Founders record live audio in the browser via dashboard `MediaRecorder` or upload pre-recorded audio/video files (`.webm`, `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`).
2. **Qwen ASR Flash STT**: The speech-to-text engine (`qwen-audio-3.0-asr-flash`) processes raw audio bytes directly with zero server-side transcoding, returning high-accuracy transcripts with word-level timestamps and punctuation.
3. **Sentinel Extractor Agent**: Sentinel receives the structured transcript, resolves referenced names against the tenant's real `EmployeeRepository`, and extracts every commitment with a verbatim source quote and confidence score.
4. **Approval Safety Gate**: Extracted tasks automatically land in the `pending_approval` queue by schema default for the founder to approve, edit, or reject with one click.

## Scope & Decisions

### 1. Locked Decisions
- **STT Engine**: Using Alibaba Cloud Qwen ASR Flash (`qwen-audio-3.0-asr-flash`).
- **Format Compatibility**: Direct native support for browser-produced formats (`.webm`, `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`) without requiring external `ffmpeg` binaries.
- **Tenant Scoping**: All `Meeting` and `TranscriptSegment` records are strictly scoped to `company_id`.
- **Approval Schema Default**: Every extracted task lands in `pending_approval` unless auto-approve threshold conditions are met.

### 2. Database Schema
- **`Meeting` model (`meetings` table)**:
  - `id`: UUID (Primary Key)
  - `company_id`: UUID (Tenant foreign key)
  - `title`: String(255)
  - `recorded_at`: DateTime (timezone-aware)
  - `duration_seconds`: Integer (nullable)
  - `audio_filename`: String(255) (nullable)
  - `audio_format`: String(50) (e.g. `webm`, `wav`, `mp3`, `m4a`)
  - `raw_transcript`: Text (nullable)
  - `status`: Enum `MeetingStatus` (`pending`, `transcribing`, `extracting`, `completed`, `failed`)
  - `error_message`: Text (nullable)
  - `created_at`, `updated_at` timestamps
- **`TranscriptSegment` model (`transcript_segments` table)**:
  - `id`: UUID (Primary Key)
  - `meeting_id`: UUID (FK to `meetings.id` ondelete `CASCADE`)
  - `company_id`: UUID (FK to `companies.id` ondelete `CASCADE`)
  - `speaker_label`: String(100) (default `"Speaker 1"`)
  - `speaker_employee_id`: UUID (nullable, FK to `employees.id`)
  - `start_time`: Float (seconds)
  - `end_time`: Float (seconds)
  - `text`: Text
  - `created_at`, `updated_at` timestamps

### 3. API Surface (`/api/v1/meetings`)
- `POST /api/v1/meetings/audio`: Multipart audio file upload (`.webm`, `.wav`, `.mp3`, `.m4a`), transcribes via Qwen ASR Flash and runs Extractor Agent.
- `POST /api/v1/meetings/text`: Direct transcript text / notes ingestion and extraction.
- `GET /api/v1/meetings`: Paginated list of recent meetings for the tenant.
- `GET /api/v1/meetings/{id}`: Detailed meeting view with status, transcript segments, and extracted tasks.

### 4. Verification & Testing
- Automated test suite verifying audio upload, Qwen ASR Flash integration, transcript segment persistence, extractor task generation into `pending_approval`, and tenant isolation.
