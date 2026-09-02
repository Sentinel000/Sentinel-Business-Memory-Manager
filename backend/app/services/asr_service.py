"""ASR Speech-to-Text service utilizing Qwen ASR Flash (qwen-audio-3.0-asr-flash)."""

import base64
import logging
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)

DASHSCOPE_ASR_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_ASR_MODEL = "qwen-audio-3.0-asr-flash"


class QwenAudioClient:
    """Client for DashScope Qwen ASR Flash model."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.qwen_api_key
        self.base_url = base_url or DASHSCOPE_ASR_URL

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav",
        sample_rate: int | None = None,
    ) -> dict[str, Any]:
        """Transcribe audio bytes to text and timestamps using Qwen ASR Flash."""
        if not self.api_key:
            # Fail loudly. Returning empty text here produced a meeting that
            # transcribed to nothing and extracted no tasks, with no error anywhere —
            # a misconfigured deploy looked like a quiet meeting.
            raise RuntimeError(
                "QWEN_API_KEY is not configured. Set it in .env — see backend/.env.example."
            )

        # Normalize audio format
        fmt = audio_format.lower().replace(".", "").replace("audio/", "").replace(";codecs=opus", "")
        if fmt in ["webm", "opus"]:
            fmt = "webm"
        elif fmt in ["m4a", "mp4", "aac"]:
            fmt = "m4a"
        elif fmt in ["ogg"]:
            fmt = "ogg"
        elif fmt in ["mp3", "mpeg"]:
            fmt = "mp3"
        elif fmt in ["flac"]:
            fmt = "flac"
        else:
            fmt = "wav"

        b64_data = base64.b64encode(audio_bytes).decode("utf-8")
        data_uri = f"data:audio/{fmt};base64,{b64_data}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": DEFAULT_ASR_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"audio": data_uri}
                        ],
                    }
                ]
            },
            "parameters": {
                "format": fmt,
            },
        }
        if sample_rate:
            payload["parameters"]["sample_rate"] = sample_rate

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                logger.error(f"Qwen ASR error: {response.status_code} {response.text}")
                # Check for silent audio error
                if "ASR_RESPONSE_HAVE_NO_WORDS" in response.text:
                    return {
                        "text": "",
                        "duration_seconds": 0,
                        "segments": [],
                        "words": [],
                    }
                raise RuntimeError(f"Qwen ASR failed with status {response.status_code}: {response.text}")

            data = response.json()
            output = data.get("output", {})
            sentence = output.get("sentence", {}) or {}
            full_text = sentence.get("text", "")
            duration = output.get("usage", {}).get("duration", 0) or data.get("usage", {}).get("duration", 0)
            words = sentence.get("words", [])

            return {
                "text": full_text,
                "duration_seconds": int(duration) if duration else 0,
                "segments": [
                    {
                        "start_time": (sentence.get("begin_time", 0) or 0) / 1000.0,
                        "end_time": (sentence.get("end_time", 0) or 0) / 1000.0,
                        "text": full_text,
                    }
                ] if full_text else [],
                "words": words,
            }
        except requests.RequestException as e:
            logger.exception("Network error contacting Qwen ASR service")
            raise RuntimeError(f"ASR service communication error: {str(e)}") from e


_client_instance: QwenAudioClient | None = None


def get_asr_client() -> QwenAudioClient:
    """Return singleton ASR client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = QwenAudioClient()
    return _client_instance
