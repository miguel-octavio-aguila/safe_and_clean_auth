import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safe_and_clean_auth.settings')

app = Celery('safe_and_clean_auth')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
