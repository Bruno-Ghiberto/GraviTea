"""Ventas app configuration."""

from django.apps import AppConfig


class VentasConfig(AppConfig):
    """Configuration for Ventas (Sales) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ventas"
    label = "gravitea_ventas"
    verbose_name = "Ventas"
