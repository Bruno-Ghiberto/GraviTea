"""Acopio app configuration."""

from django.apps import AppConfig


class AcopioConfig(AppConfig):
    """Configuration for Acopio (Grain Elevator) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.acopio"
    label = "gravitea_acopio"
    verbose_name = "Acopio"
