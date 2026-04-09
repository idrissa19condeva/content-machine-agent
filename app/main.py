from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
import sentry_sdk

from app.config import get_settings
from app.api.routes import projects, ideas, pipeline, publications, analytics

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer() if settings.app_debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
)

# ── Sentry ───────────────────────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    structlog.get_logger().info("Content Machine démarré")
    yield
    structlog.get_logger().info("Content Machine arrêté")


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Content Machine",
    description="Plateforme de création de contenu vidéo automatisée par IA",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(projects.router, prefix="/api/v1")
app.include_router(ideas.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(publications.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
