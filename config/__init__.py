"""
Settings module initialization.
This allows us to import settings directly using:
from django.conf import settings
"""

import os
from .celery import app as celery_app

__all__ = ["celery_app"]

settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
