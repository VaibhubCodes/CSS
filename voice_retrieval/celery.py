# voice_retrieval/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_retrieval.settings')

app = Celery('voice_retrieval')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
