"""
Tâches Celery asynchrones.
Ces tâches sont exécutées en arrière-plan par les workers.
"""
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.workers.celery_app import celery_app
from app.models.database import async_session
from app.models.entities import PublicationJob, PerformanceMetric
from sqlalchemy import select

import structlog

logger = structlog.get_logger()


def _run_async(coro):
    """Helper pour exécuter du code async dans un worker Celery sync."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.run_content_pipeline", bind=True, max_retries=2)
def run_content_pipeline(self, idea_id: str):
    """Lance le pipeline complet pour une idée."""

    async def _run():
        from app.services.orchestrator import PipelineOrchestrator

        async with async_session() as db:
            orchestrator = PipelineOrchestrator(db)
            result = await orchestrator.run_full_pipeline(UUID(idea_id))
            return result

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("Pipeline échoué", idea_id=idea_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.tasks.collect_metrics_task")
def collect_metrics_task(publication_id: str):
    """Collecte les métriques d'un post publié."""

    async def _run():
        from app.agents import AnalyticsAgent

        async with async_session() as db:
            job = await db.get(PublicationJob, UUID(publication_id))
            if not job or not job.platform_post_id:
                return {"error": "Post non publié"}

            agent = AnalyticsAgent()
            metrics = await agent.run(
                {"platform": job.platform.value, "platform_post_id": job.platform_post_id},
                db_session=db,
            )

            metric = PerformanceMetric(
                publication_id=UUID(publication_id),
                views=metrics.get("views", 0),
                likes=metrics.get("likes", 0),
                comments=metrics.get("comments", 0),
                shares=metrics.get("shares", 0),
                watch_time_avg_sec=metrics.get("watch_time_avg_sec", 0),
                engagement_rate=metrics.get("engagement_rate", 0),
            )
            db.add(metric)
            await db.commit()
            return {"status": "collected", "publication_id": publication_id}

    return _run_async(_run())


@celery_app.task(name="app.workers.tasks.collect_all_metrics")
def collect_all_metrics():
    """Collecte les métriques de tous les posts publiés."""

    async def _run():
        async with async_session() as db:
            result = await db.execute(
                select(PublicationJob).where(PublicationJob.status == "published")
            )
            jobs = result.scalars().all()
            for job in jobs:
                collect_metrics_task.delay(str(job.id))
            return {"triggered": len(jobs)}

    return _run_async(_run())


@celery_app.task(name="app.workers.tasks.process_scheduled_publications")
def process_scheduled_publications():
    """Publie les vidéos dont l'heure de publication est passée."""

    async def _run():
        from app.agents import PublishingAgent
        from app.services.storage import get_presigned_url

        async with async_session() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(PublicationJob)
                .where(PublicationJob.status == "pending")
                .where(PublicationJob.scheduled_at <= now)
            )
            jobs = result.scalars().all()

            published = 0
            for job in jobs:
                try:
                    video = await db.get(
                        __import__("app.models.entities", fromlist=["VideoAsset"]).VideoAsset,
                        job.video_id,
                    )
                    if not video:
                        continue

                    video_url = await get_presigned_url(video.file_key, expires_in=7200)

                    agent = PublishingAgent()
                    pub_result = await agent.run(
                        {
                            "video_file_url": video_url,
                            "platform": job.platform.value,
                            "caption": job.caption,
                            "hashtags": job.hashtags,
                        },
                        db_session=db,
                    )

                    job.status = "published"
                    job.published_at = datetime.now(timezone.utc)
                    job.platform_post_id = pub_result.get("platform_post_id")
                    published += 1

                except Exception as e:
                    job.status = "failed"
                    job.error_message = str(e)
                    logger.error("Publication échouée", job_id=str(job.id), error=str(e))

            await db.commit()
            return {"published": published, "total_pending": len(jobs)}

    return _run_async(_run())
