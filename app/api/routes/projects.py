from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db, Project
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.active == True).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: UUID, payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    project.active = False
    await db.flush()
