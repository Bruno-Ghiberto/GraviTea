"""Compras app configuration."""

from django.apps import AppConfig


class ComprasConfig(AppConfig):
    """Configuration for Compras (Purchases) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.compras"
    label = "gravitea_compras"
    verbose_name = "Compras"
