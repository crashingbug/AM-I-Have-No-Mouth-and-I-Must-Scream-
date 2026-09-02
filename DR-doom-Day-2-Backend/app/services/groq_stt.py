import io
import requests

from app.settings import settings

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class GroqSttError(RuntimeError):
    pass


# ==============================================================================
# PHASE 1: THE EARS (Speech-to-Text with Groq Whisper)
# ==============================================================================
def transcribe(audio: bytes, filename: str, content_type: str) -> str:
    """
    Send user audio recording bytes to Groq Whisper and return transcribed text.
    1. Check if settings.groq_api_key is set. If not, raise GroqSttError("Groq is not configured.")
    2. Set Authorization header with Bearer token.
    3. Build multipart payload with (filename, io.BytesIO(audio), content_type) and model 'whisper-large-v3-turbo'.
    4. Send POST to GROQ_TRANSCRIBE_URL and return the trimmed transcript string.
    """
    if not settings.groq_api_key or settings.groq_api_key.startswith("your_actual_groq_api_key"):
        raise GroqSttError("Groq is not configured.")

    try:
        response = requests.post(
            GROQ_TRANSCRIBE_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
            },
            files={
                "file": (filename or "recording.webm", io.BytesIO(audio), content_type or "audio/webm"),
                "model": (None, "whisper-large-v3-turbo"),
            },
            timeout=15.0,
        )
    except Exception as exc:
        raise GroqSttError("Unable to reach speech transcription service.") from exc

    if response.status_code != 200:
        error_detail = ""
        try:
            error_detail = response.json().get("error", {}).get("message", "")
        except Exception:
            error_detail = response.text
        raise GroqSttError(error_detail or f"Speech transcription failed with status {response.status_code}.")

    data = response.json()
    transcript = data.get("text", "")
    return transcript.strip()
