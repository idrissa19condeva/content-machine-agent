import uuid
from app.agents.base import BaseAgent
from app.services.video import assemble_video
from app.services.storage import upload_file


class VideoAssemblyAgent(BaseAgent):
    """
    Assemble la vidéo finale : fond + voix off + sous-titres + musique + branding.
    Entrées : audio URL, script (pour sous-titres), brand_config
    Sorties : URL de la vidéo finale, durée, résolution
    """

    name = "video_assembly"

    async def execute(self, input_data: dict) -> dict:
        audio_key = input_data["audio_file_key"]
        script_text = input_data["full_text"]
        brand_config = input_data.get("brand_config", {})
        background_video = input_data.get("background_video")  # optionnel

        # Assembler la vidéo via FFmpeg
        video_bytes, duration_sec = await assemble_video(
            audio_key=audio_key,
            script_text=script_text,
            brand_config=brand_config,
            background_video=background_video,
        )

        file_key = f"videos/{uuid.uuid4()}.mp4"
        file_url = await upload_file(video_bytes, file_key, content_type="video/mp4")

        return {
            "file_url": file_url,
            "file_key": file_key,
            "duration_sec": duration_sec,
            "resolution": "1080x1920",
            "has_subtitles": True,
            "has_music": True,
            "has_branding": bool(brand_config),
        }
