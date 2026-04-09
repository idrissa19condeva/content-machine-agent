from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db
from app.schemas import PipelineRequest, PipelineStatus
from app.workers.tasks import run_content_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineStatus)
async def trigger_pipeline(payload: PipelineRequest, db: AsyncSession = Depends(get_db)):
    """Lance le pipeline complet en tâche asynchrone Celery."""
    task = run_content_pipeline.delay(str(payload.idea_id))
    return PipelineStatus(
        idea_id=payload.idea_id,
        current_step="queued",
        status="pending",
        details={"celery_task_id": task.id},
    )


@router.get("/status/{task_id}")
async def pipeline_status(task_id: str):
    """Vérifie le statut d'une tâche pipeline."""
    from app.workers.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
