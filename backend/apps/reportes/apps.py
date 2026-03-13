"""Reportes app configuration."""

from django.apps import AppConfig


class ReportesConfig(AppConfig):
    """Configuration for Reportes (Reports) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reportes"
    label = "gravitea_reportes"
    verbose_name = "Reportes"
