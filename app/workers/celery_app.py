from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "content_machine",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # une tâche à la fois par worker (tâches lourdes)
    task_soft_time_limit=600,  # 10 min soft limit
    task_time_limit=900,  # 15 min hard limit
)

# ── Tâches planifiées (Celery Beat) ──────────────────────────────────
celery_app.conf.beat_schedule = {
    # Collecte des métriques toutes les 6 heures
    "collect-all-metrics": {
        "task": "app.workers.tasks.collect_all_metrics",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Vérifier les publications programmées toutes les 5 minutes
    "check-scheduled-publications": {
        "task": "app.workers.tasks.process_scheduled_publications",
        "schedule": crontab(minute="*/5"),
    },
}
