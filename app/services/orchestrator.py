"""
Orchestrateur du pipeline de contenu.
Coordonne l'exécution séquentielle des agents pour transformer
une idée approuvée en vidéo publiée.
"""
import structlog
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import (
    ContentIdea, Script, VoiceAsset, VideoAsset, PublicationJob, ContentStatus, Project
)
from app.agents import (
    ScriptWriterAgent,
    HookOptimizerAgent,
    VoiceGenerationAgent,
    VideoAssemblyAgent,
)

logger = structlog.get_logger()


class PipelineOrchestrator:
    """
    Pipeline : Idée → Script → Hook Optimisé → Voix → Vidéo → Prêt à publier

    Chaque étape :
    1. Lit l'état courant en BDD
    2. Exécute l'agent correspondant
    3. Persiste le résultat
    4. Passe à l'étape suivante
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_full_pipeline(self, idea_id: UUID) -> dict:
        """Exécute le pipeline complet pour une idée approuvée."""

        # Charger l'idée et le projet
        idea = await self.db.get(ContentIdea, idea_id)
        if not idea:
            raise ValueError(f"Idée introuvable : {idea_id}")
        if not idea.approved:
            raise ValueError(f"Idée non approuvée : {idea_id}")

        project = await self.db.get(Project, idea.project_id)

        steps_result = {"idea_id": str(idea_id), "steps": {}}

        # ── Étape 1 : Script ──────────────────────────────────────────
        logger.info("Pipeline: génération du script", idea_id=str(idea_id))
        script_agent = ScriptWriterAgent()
        script_result = await script_agent.run(
            {
                "topic": idea.topic,
                "hook": idea.metadata_.get("hook", ""),
                "niche": project.niche.value,
                "language": project.language,
                "project_id": str(project.id),
            },
            db_session=self.db,
        )

        script = Script(
            idea_id=idea.id,
            hook=script_result.get("hook", ""),
            body=script_result.get("body", ""),
            cta=script_result.get("cta", ""),
            full_text=script_result.get("full_text", ""),
            word_count=script_result.get("word_count", 0),
            estimated_duration_sec=script_result.get("estimated_duration_sec", 0),
            llm_model_used=project.language,
        )
        self.db.add(script)
        await self.db.flush()
        steps_result["steps"]["script"] = "done"

        # ── Étape 2 : Optimisation du hook ────────────────────────────
        logger.info("Pipeline: optimisation du hook")
        hook_agent = HookOptimizerAgent()
        hook_result = await hook_agent.run(
            {
                "full_text": script.full_text,
                "niche": project.niche.value,
                "project_id": str(project.id),
            },
            db_session=self.db,
        )

        # Appliquer le meilleur hook
        hooks = hook_result.get("hooks", [])
        if hooks:
            best_hook = hooks[0]["text"]
            script.hook = best_hook
            script.full_text = best_hook + "\n" + script.body + "\n" + script.cta
        steps_result["steps"]["hook_optimization"] = "done"

        # ── Étape 3 : Voix off ───────────────────────────────────────
        logger.info("Pipeline: génération voix off")
        voice_agent = VoiceGenerationAgent()
        voice_result = await voice_agent.run(
            {
                "full_text": script.full_text,
                "voice_id": project.brand_config.get("voice_id"),
                "tts_provider": project.brand_config.get("tts_provider", "elevenlabs"),
                "project_id": str(project.id),
            },
            db_session=self.db,
        )

        voice_asset = VoiceAsset(
            script_id=script.id,
            file_url=voice_result["file_url"],
            file_key=voice_result["file_key"],
            duration_sec=voice_result["duration_sec"],
            tts_provider=voice_result["tts_provider"],
            voice_id=voice_result.get("voice_id"),
        )
        self.db.add(voice_asset)
        await self.db.flush()
        steps_result["steps"]["voice"] = "done"

        # ── Étape 4 : Assemblage vidéo ────────────────────────────────
        logger.info("Pipeline: assemblage vidéo")
        video_agent = VideoAssemblyAgent()
        video_result = await video_agent.run(
            {
                "audio_file_key": voice_asset.file_key,
                "full_text": script.full_text,
                "brand_config": project.brand_config,
                "project_id": str(project.id),
            },
            db_session=self.db,
        )

        video_asset = VideoAsset(
            script_id=script.id,
            file_url=video_result["file_url"],
            file_key=video_result["file_key"],
            duration_sec=video_result["duration_sec"],
            resolution=video_result.get("resolution", "1080x1920"),
            has_subtitles=video_result.get("has_subtitles", True),
            has_music=video_result.get("has_music", True),
            has_branding=video_result.get("has_branding", False),
            status=ContentStatus.VIDEO_READY,
        )
        self.db.add(video_asset)
        await self.db.flush()
        steps_result["steps"]["video"] = "done"

        await self.db.commit()
        logger.info("Pipeline terminé avec succès", idea_id=str(idea_id))
        steps_result["status"] = "completed"
        steps_result["video_id"] = str(video_asset.id)
        steps_result["video_url"] = video_asset.file_url

        return steps_result
