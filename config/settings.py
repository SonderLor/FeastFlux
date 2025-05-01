import os

settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
