import edge_tts

from app.schemas import Voice

VOICES = (
    Voice(id="en-US-GuyNeural", label="Guy — US English"),
    Voice(id="en-GB-RyanNeural", label="Ryan — UK English"),
    Voice(id="en-US-JennyNeural", label="Jenny — US English"),
)
VOICE_IDS = {voice.id for voice in VOICES}


class EdgeTtsError(RuntimeError):
    pass


def available_voices() -> list[Voice]:
    return list(VOICES)


# ==============================================================================
# PHASE 3: THE MOUTH (Neural Text-to-Speech Streaming)
# ==============================================================================
async def generate_speech(text: str, voice_id: str) -> bytes:
    """
    Synthesize text into MP3 audio bytes using Microsoft Edge TTS.
    1. Validate voice_id is in VOICE_IDS (raise EdgeTtsError if not).
    2. Instantiate stream = edge_tts.Communicate(text=text, voice=voice_id).
    3. Stream audio chunks into a bytearray where chunk["type"] == "audio".
    4. Return bytes(audio).
    """
    if voice_id not in VOICE_IDS:
        raise EdgeTtsError(f"Unsupported voice ID: {voice_id}")

    try:
        communicate = edge_tts.Communicate(text=text, voice=voice_id)
        audio = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
        return bytes(audio)
    except Exception as exc:
        raise EdgeTtsError(f"Speech synthesis failed: {exc}") from exc
