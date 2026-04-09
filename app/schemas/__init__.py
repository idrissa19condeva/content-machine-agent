from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.entities import ContentStatus, Platform, Niche


# ─── Project ────────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    niche: Niche = Niche.BUSINESS_TIPS
    target_platform: Platform = Platform.BOTH
    language: str = "fr"
    brand_config: dict = {}
    posting_schedule: dict = {}


class ProjectOut(ProjectCreate):
    id: UUID
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Content Idea ────────────────────────────────────────────────────────
class IdeaCreate(BaseModel):
    topic: str = Field(..., max_length=300)
    source: str = "manual"


class IdeaOut(BaseModel):
    id: UUID
    project_id: UUID
    topic: str
    source: str
    trend_score: float
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IdeaApproval(BaseModel):
    approved: bool


# ─── Script ──────────────────────────────────────────────────────────────
class ScriptOut(BaseModel):
    id: UUID
    idea_id: UUID
    hook: str
    body: str
    cta: str
    full_text: str
    word_count: int
    estimated_duration_sec: int
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Voice ───────────────────────────────────────────────────────────────
class VoiceAssetOut(BaseModel):
    id: UUID
    script_id: UUID
    file_url: str
    duration_sec: float
    tts_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Video ───────────────────────────────────────────────────────────────
class VideoAssetOut(BaseModel):
    id: UUID
    script_id: UUID
    file_url: str
    duration_sec: float
    resolution: str
    status: ContentStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Publication ─────────────────────────────────────────────────────────
class PublicationCreate(BaseModel):
    video_id: UUID
    platform: Platform
    scheduled_at: datetime
    caption: str = ""
    hashtags: list[str] = []


class PublicationOut(BaseModel):
    id: UUID
    video_id: UUID
    platform: Platform
    scheduled_at: datetime
    caption: str
    hashtags: list[str]
    status: str
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Metrics ─────────────────────────────────────────────────────────────
class MetricsOut(BaseModel):
    id: UUID
    publication_id: UUID
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_avg_sec: float
    engagement_rate: float
    collected_at: datetime

    class Config:
        from_attributes = True


# ─── Pipeline ────────────────────────────────────────────────────────────
class PipelineRequest(BaseModel):
    """Lance le pipeline complet pour une idée approuvée."""
    idea_id: UUID


class PipelineStatus(BaseModel):
    idea_id: UUID
    current_step: str
    status: str
    details: dict = {}


class GenerateIdeasRequest(BaseModel):
    count: int = Field(5, ge=1, le=20)
    niche: Optional[Niche] = None
