import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.database import Base
import enum


class ContentStatus(str, enum.Enum):
    IDEA = "idea"
    SCRIPTED = "scripted"
    AUDIO_READY = "audio_ready"
    VIDEO_READY = "video_ready"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class Platform(str, enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    BOTH = "both"


class Niche(str, enum.Enum):
    BUSINESS_TIPS = "business_tips"
    MOTIVATION = "motivation"
    FUN_FACTS = "fun_facts"
    CUSTOM = "custom"


# ─── Project ────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    niche = Column(SAEnum(Niche), nullable=False, default=Niche.BUSINESS_TIPS)
    target_platform = Column(SAEnum(Platform), default=Platform.BOTH)
    language = Column(String(10), default="fr")
    brand_config = Column(JSON, default=dict)  # couleurs, logo, police, watermark
    posting_schedule = Column(JSON, default=dict)  # {"days": [0,2,4], "times": ["09:00","18:00"]}
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content_ideas = relationship("ContentIdea", back_populates="project", cascade="all, delete-orphan")


# ─── Content Idea ────────────────────────────────────────────────────────
class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    topic = Column(String(300), nullable=False)
    source = Column(String(100))  # trending, manual, ai_generated, competitor
    trend_score = Column(Float, default=0.0)
    approved = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="content_ideas")
    script = relationship("Script", back_populates="idea", uselist=False, cascade="all, delete-orphan")


# ─── Script ──────────────────────────────────────────────────────────────
class Script(Base):
    __tablename__ = "scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idea_id = Column(UUID(as_uuid=True), ForeignKey("content_ideas.id"), nullable=False, unique=True)
    hook = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    cta = Column(Text, default="")
    full_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    estimated_duration_sec = Column(Integer, default=0)
    llm_model_used = Column(String(100))
    prompt_used = Column(Text)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    idea = relationship("ContentIdea", back_populates="script")
    voice_asset = relationship("VoiceAsset", back_populates="script", uselist=False, cascade="all, delete-orphan")
    video_asset = relationship("VideoAsset", back_populates="script", uselist=False, cascade="all, delete-orphan")


# ─── Voice Asset ─────────────────────────────────────────────────────────
class VoiceAsset(Base):
    __tablename__ = "voice_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False, unique=True)
    file_url = Column(String(500), nullable=False)
    file_key = Column(String(300), nullable=False)  # S3 key
    duration_sec = Column(Float, default=0.0)
    tts_provider = Column(String(50))
    voice_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    script = relationship("Script", back_populates="voice_asset")


# ─── Video Asset ─────────────────────────────────────────────────────────
class VideoAsset(Base):
    __tablename__ = "video_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False, unique=True)
    file_url = Column(String(500), nullable=False)
    file_key = Column(String(300), nullable=False)
    duration_sec = Column(Float, default=0.0)
    resolution = Column(String(20), default="1080x1920")
    has_subtitles = Column(Boolean, default=True)
    has_music = Column(Boolean, default=True)
    has_branding = Column(Boolean, default=True)
    status = Column(SAEnum(ContentStatus), default=ContentStatus.VIDEO_READY)
    created_at = Column(DateTime, default=datetime.utcnow)

    script = relationship("Script", back_populates="video_asset")
    publication_job = relationship("PublicationJob", back_populates="video", uselist=False, cascade="all, delete-orphan")


# ─── Publication Job ─────────────────────────────────────────────────────
class PublicationJob(Base):
    __tablename__ = "publication_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("video_assets.id"), nullable=False, unique=True)
    platform = Column(SAEnum(Platform), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    caption = Column(Text, default="")
    hashtags = Column(JSON, default=list)
    status = Column(String(30), default="pending")  # pending, publishing, published, failed
    published_at = Column(DateTime, nullable=True)
    platform_post_id = Column(String(200), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoAsset", back_populates="publication_job")
    metrics = relationship("PerformanceMetric", back_populates="publication", cascade="all, delete-orphan")


# ─── Performance Metrics ────────────────────────────────────────────────
class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_id = Column(UUID(as_uuid=True), ForeignKey("publication_jobs.id"), nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    watch_time_avg_sec = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    collected_at = Column(DateTime, default=datetime.utcnow)

    publication = relationship("PublicationJob", back_populates="metrics")


# ─── Agent Run (audit trail) ────────────────────────────────────────────
class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    status = Column(String(30), default="running")  # running, success, failed
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


# ─── Prompt Template ────────────────────────────────────────────────────
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    agent_name = Column(String(100), nullable=False)
    template = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
