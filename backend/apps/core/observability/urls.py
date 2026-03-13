"""
URL configuration for observability endpoints.

Provides:
- /metrics - Prometheus metrics endpoint
"""

from django.urls import path

from .views import MetricsView

app_name = "observability"

urlpatterns = [
    path("metrics", MetricsView.as_view(), name="metrics"),
]
