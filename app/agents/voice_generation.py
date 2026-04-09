from app.agents.base import BaseAgent
from app.services.tts import generate_speech
from app.services.storage import upload_file
import uuid


class VoiceGenerationAgent(BaseAgent):
    """
    Génère la voix off à partir du script.
    Entrées : texte du script, voice_id, provider
    Sorties : URL du fichier audio, durée
    """

    name = "voice_generation"

    async def execute(self, input_data: dict) -> dict:
        text = input_data["full_text"]
        voice_id = input_data.get("voice_id")
        provider = input_data.get("tts_provider", "elevenlabs")

        # Générer l'audio
        audio_bytes, duration_sec = await generate_speech(
            text=text,
            voice_id=voice_id,
            provider=provider,
        )

        # Upload vers S3
        file_key = f"voice/{uuid.uuid4()}.mp3"
        file_url = await upload_file(audio_bytes, file_key, content_type="audio/mpeg")

        return {
            "file_url": file_url,
            "file_key": file_key,
            "duration_sec": duration_sec,
            "tts_provider": provider,
            "voice_id": voice_id,
        }
