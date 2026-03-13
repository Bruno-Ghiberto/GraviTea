"""Inventario app configuration."""

from django.apps import AppConfig


class InventarioConfig(AppConfig):
    """Configuration for Inventario app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventario"
    verbose_name = "Inventory Management"
