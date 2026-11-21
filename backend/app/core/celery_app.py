from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

_includes = ["app.tasks.conversation_tasks"]
try:
    from commercial.celery_ext import BEAT_SCHEDULE, EXTRA_INCLUDES
except ImportError:
    BEAT_SCHEDULE = {}
    EXTRA_INCLUDES = []
_includes.extend(EXTRA_INCLUDES)

celery_app = Celery(
    "falitong",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=_includes,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "conversation-history-cleanup-daily": {
        "task": "app.tasks.conversation_tasks.cleanup_expired_conversations",
        "schedule": crontab(hour=3, minute=0),
    },
    **BEAT_SCHEDULE,
}
