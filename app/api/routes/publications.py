from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db, PublicationJob, VideoAsset
from app.schemas import PublicationCreate, PublicationOut

router = APIRouter(prefix="/publications", tags=["publications"])


@router.post("/", response_model=PublicationOut, status_code=201)
async def schedule_publication(payload: PublicationCreate, db: AsyncSession = Depends(get_db)):
    video = await db.get(VideoAsset, payload.video_id)
    if not video:
        raise HTTPException(404, "Vidéo introuvable")

    job = PublicationJob(
        video_id=payload.video_id,
        platform=payload.platform,
        scheduled_at=payload.scheduled_at,
        caption=payload.caption,
        hashtags=payload.hashtags,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


@router.get("/", response_model=list[PublicationOut])
async def list_publications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PublicationJob).order_by(PublicationJob.scheduled_at.desc()))
    return result.scalars().all()


@router.get("/{job_id}", response_model=PublicationOut)
async def get_publication(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(PublicationJob, job_id)
    if not job:
        raise HTTPException(404, "Publication introuvable")
    return job
