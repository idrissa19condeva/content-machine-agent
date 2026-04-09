from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db, ContentIdea, Project
from app.schemas import IdeaCreate, IdeaOut, IdeaApproval, GenerateIdeasRequest
from app.agents import TrendResearchAgent

router = APIRouter(prefix="/projects/{project_id}/ideas", tags=["ideas"])


@router.post("/generate", response_model=list[IdeaOut])
async def generate_ideas(
    project_id: UUID,
    payload: GenerateIdeasRequest,
    db: AsyncSession = Depends(get_db),
):
    """Génère des idées via l'agent de recherche de tendances."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")

    agent = TrendResearchAgent()
    result = await agent.run(
        {"niche": project.niche.value, "language": project.language, "count": payload.count, "project_id": str(project_id)},
        db_session=db,
    )

    ideas = []
    for item in result.get("ideas", []):
        idea = ContentIdea(
            project_id=project_id,
            topic=item["topic"],
            source="ai_generated",
            trend_score=item.get("trend_score", 0),
            metadata_={"hook": item.get("hook", ""), "reasoning": item.get("reasoning", "")},
        )
        db.add(idea)
        ideas.append(idea)
    await db.flush()
    for idea in ideas:
        await db.refresh(idea)
    return ideas


@router.post("/", response_model=IdeaOut, status_code=201)
async def create_idea(project_id: UUID, payload: IdeaCreate, db: AsyncSession = Depends(get_db)):
    idea = ContentIdea(project_id=project_id, **payload.model_dump())
    db.add(idea)
    await db.flush()
    await db.refresh(idea)
    return idea


@router.get("/", response_model=list[IdeaOut])
async def list_ideas(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ContentIdea).where(ContentIdea.project_id == project_id).order_by(ContentIdea.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{idea_id}/approve", response_model=IdeaOut)
async def approve_idea(project_id: UUID, idea_id: UUID, payload: IdeaApproval, db: AsyncSession = Depends(get_db)):
    idea = await db.get(ContentIdea, idea_id)
    if not idea or idea.project_id != project_id:
        raise HTTPException(404, "Idée introuvable")
    idea.approved = payload.approved
    idea.rejected = not payload.approved
    await db.flush()
    await db.refresh(idea)
    return idea
