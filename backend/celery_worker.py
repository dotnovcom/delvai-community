"""Celery worker 启动入口

用法:
  cd backend
  celery -A celery_worker worker --loglevel=info
  celery -A celery_worker beat --loglevel=info
"""
from app.core.celery_app import celery_app

app = celery_app
