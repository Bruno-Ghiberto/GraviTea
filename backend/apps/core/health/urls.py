"""
Health check URL routing.

Maps health check endpoints to their views:
- /health/live - Liveness probe
- /health/ready - Readiness probe
- /health/startup - Startup probe

Per spec.md FR-019 through FR-023 requirements.
"""

from django.urls import path

from apps.core.health.views import LivenessView, ReadinessView, StartupView

app_name = "health"

urlpatterns = [
    path("live", LivenessView.as_view(), name="live"),
    path("ready", ReadinessView.as_view(), name="ready"),
    path("startup", StartupView.as_view(), name="startup"),
]
