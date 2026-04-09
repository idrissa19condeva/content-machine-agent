import httpx
import struct
from typing import Optional
from app.config import get_settings

settings = get_settings()


async def generate_speech(
    text: str,
    voice_id: Optional[str] = None,
    provider: str = "elevenlabs",
) -> tuple[bytes, float]:
    """Génère un fichier audio à partir de texte. Retourne (bytes, duration_sec)."""

    if provider == "elevenlabs":
        return await _elevenlabs_tts(text, voice_id or settings.elevenlabs_voice_id)
    elif provider == "openai":
        return await _openai_tts(text, voice_id or "alloy")
    else:
        raise ValueError(f"TTS provider inconnu : {provider}")


async def _elevenlabs_tts(text: str, voice_id: str) -> tuple[bytes, float]:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        audio_bytes = resp.content

    duration = _estimate_duration_from_text(text)
    return audio_bytes, duration


async def _openai_tts(text: str, voice: str) -> tuple[bytes, float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.audio.speech.create(model="tts-1", voice=voice, input=text)
    audio_bytes = response.content
    duration = _estimate_duration_from_text(text)
    return audio_bytes, duration


def _estimate_duration_from_text(text: str) -> float:
    """Estimation grossière : ~150 mots/minute."""
    words = len(text.split())
    return round(words / 150 * 60, 1)
