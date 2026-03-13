"""Sync app configuration."""

from django.apps import AppConfig


class SyncConfig(AppConfig):
    """Configuration for Sync app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sync"
    verbose_name = "Offline Synchronization"
