import asyncio

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.schemas import TranscriptResponse, TtsRequest, VoicesResponse
from app.services.edge_tts_service import EdgeTtsError, available_voices, generate_speech
from app.services.groq_stt import GroqSttError, transcribe

router = APIRouter(prefix="/api", tags=["speech"])
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/mp4", "audio/mpeg"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024


# ==============================================================================
# PHASE 3: THE MOUTH (Voice Catalog Endpoint)
# ==============================================================================
@router.get("/voices", response_model=VoicesResponse)
async def voices() -> VoicesResponse:
    return VoicesResponse(voices=available_voices())


# ==============================================================================
# PHASE 3: THE MOUTH (Text-to-Speech Streaming Endpoint)
# ==============================================================================
@router.post("/tts", response_class=Response)
async def tts(request: TtsRequest) -> Response:
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="TTS text cannot be empty.",
        )

    try:
        audio = await generate_speech(text, request.voice_id)
    except EdgeTtsError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize speech: {exc}",
        ) from exc

    return Response(content=audio, media_type="audio/mpeg")


# ==============================================================================
# PHASE 1: THE EARS (Audio Transcription Upload Endpoint)
# ==============================================================================
@router.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscriptResponse:
    content_type = (audio.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Audio type '{audio.content_type}' is not supported.",
        )

    try:
        audio_bytes = await audio.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded audio stream.",
        ) from exc

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded audio payload cannot be empty.",
        )

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio payload exceeds maximum size of {MAX_AUDIO_BYTES} bytes.",
        )

    try:
        transcript = await asyncio.to_thread(
            transcribe,
            audio_bytes,
            audio.filename or "recording.webm",
            content_type,
        )
    except GroqSttError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        ) from exc

    return TranscriptResponse(transcript=transcript)
