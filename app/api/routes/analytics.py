from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db, PerformanceMetric, PublicationJob
from app.schemas import MetricsOut
from app.workers.tasks import collect_metrics_task

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/collect/{publication_id}")
async def trigger_metrics_collection(publication_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lance la collecte de métriques pour un post publié."""
    job = await db.get(PublicationJob, publication_id)
    if not job:
        raise HTTPException(404, "Publication introuvable")
    if job.status != "published":
        raise HTTPException(400, "Le post n'est pas encore publié")

    task = collect_metrics_task.delay(str(publication_id))
    return {"task_id": task.id, "status": "collecting"}


@router.get("/{publication_id}", response_model=list[MetricsOut])
async def get_metrics(publication_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.publication_id == publication_id)
        .order_by(PerformanceMetric.collected_at.desc())
    )
    return result.scalars().all()


@router.get("/project/{project_id}/summary")
async def project_analytics_summary(project_id: UUID, db: AsyncSession = Depends(get_db)):
    """Résumé des performances d'un projet."""
    # Requête jointe pour récupérer les métriques liées au projet
    from app.models.entities import ContentIdea, Script, VideoAsset
    from sqlalchemy.orm import selectinload

    query = (
        select(PerformanceMetric)
        .join(PublicationJob)
        .join(VideoAsset)
        .join(Script)
        .join(ContentIdea)
        .where(ContentIdea.project_id == project_id)
    )
    result = await db.execute(query)
    metrics = result.scalars().all()

    if not metrics:
        return {"total_posts": 0, "total_views": 0, "avg_engagement": 0}

    return {
        "total_posts": len(metrics),
        "total_views": sum(m.views for m in metrics),
        "total_likes": sum(m.likes for m in metrics),
        "total_comments": sum(m.comments for m in metrics),
        "total_shares": sum(m.shares for m in metrics),
        "avg_engagement": round(sum(m.engagement_rate for m in metrics) / len(metrics), 2),
    }
