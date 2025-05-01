"""
Settings module initialization.
This allows us to import settings directly using:
from django.conf import settings
"""
from .celery import app as celery_app

__all__ = ["celery_app"]
