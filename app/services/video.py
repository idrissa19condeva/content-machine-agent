import asyncio
import json
import os
import tempfile
import uuid
from typing import Optional
import structlog
from app.services.storage import download_file

logger = structlog.get_logger()

# Répertoire des assets par défaut (fonds, musiques)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")


async def assemble_video(
    audio_key: str,
    script_text: str,
    brand_config: dict = None,
    background_video: Optional[str] = None,
) -> tuple[bytes, float]:
    """
    Assemble une vidéo verticale (1080x1920) avec :
    - Fond vidéo ou couleur unie
    - Voix off audio
    - Sous-titres animés (ASS)
    - Musique de fond (optionnel)
    - Watermark / branding (optionnel)

    Retourne (video_bytes, duration_sec).
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Télécharger l'audio
        audio_bytes = await download_file(audio_key)
        audio_path = os.path.join(tmpdir, "voice.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # 2. Obtenir la durée audio
        duration = await _get_audio_duration(audio_path)

        # 3. Générer le fichier de sous-titres ASS
        subs_path = os.path.join(tmpdir, "subs.ass")
        _generate_ass_subtitles(script_text, duration, subs_path, brand_config)

        # 4. Préparer le fond vidéo
        bg_path = os.path.join(tmpdir, "background.mp4")
        if background_video:
            bg_bytes = await download_file(background_video)
            with open(bg_path, "wb") as f:
                f.write(bg_bytes)
        else:
            await _generate_color_background(bg_path, duration, brand_config)

        # 5. Assembler avec FFmpeg
        output_path = os.path.join(tmpdir, "output.mp4")
        await _ffmpeg_assemble(
            bg_path=bg_path,
            audio_path=audio_path,
            subs_path=subs_path,
            output_path=output_path,
            duration=duration,
            brand_config=brand_config,
        )

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        return video_bytes, duration


async def _get_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", audio_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    data = json.loads(stdout)
    return float(data["format"]["duration"])


def _generate_ass_subtitles(text: str, duration: float, output_path: str, brand_config: dict = None):
    """Génère un fichier ASS avec des sous-titres mot par mot style TikTok."""
    font = (brand_config or {}).get("subtitle_font", "Arial")
    font_size = (brand_config or {}).get("subtitle_font_size", 24)
    color = (brand_config or {}).get("subtitle_color", "&H00FFFFFF")

    words = text.split()
    total_words = len(words)
    time_per_word = duration / max(total_words, 1)

    header = f"""[Script Info]
Title: Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,40,40,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    # Afficher par groupes de 4-6 mots
    chunk_size = 5
    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    chunk_duration = duration / max(len(chunks), 1)

    for i, chunk in enumerate(chunks):
        start = _format_ass_time(i * chunk_duration)
        end = _format_ass_time((i + 1) * chunk_duration)
        line = " ".join(chunk)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{line}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


async def _generate_color_background(output_path: str, duration: float, brand_config: dict = None):
    """Génère un fond uni animé avec un léger gradient."""
    bg_color = (brand_config or {}).get("background_color", "0x1a1a2e")

    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={bg_color}:s=1080x1920:d={duration}:r=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()


async def _ffmpeg_assemble(
    bg_path: str,
    audio_path: str,
    subs_path: str,
    output_path: str,
    duration: float,
    brand_config: dict = None,
):
    """Assemblage final FFmpeg."""
    # Filtre pour sous-titres
    vf_filter = f"ass={subs_path}"

    # Ajout watermark si configuré
    watermark = (brand_config or {}).get("watermark_text")
    if watermark:
        vf_filter += f",drawtext=text='{watermark}':fontsize=18:fontcolor=white@0.5:x=w-tw-20:y=20"

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", audio_path,
        "-vf", vf_filter,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    logger.info("FFmpeg assemblage", cmd=" ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg erreur: {stderr.decode()}")
