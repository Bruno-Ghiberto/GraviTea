"""
Health check endpoints package for Kubernetes probes.

This package provides:
- /health/live - Liveness probe (returns 200 if process is alive)
- /health/ready - Readiness probe (checks database connectivity)
- /health/startup - Startup probe (checks migrations and initial setup)

Per spec.md FR-019 through FR-023 requirements.
"""

from apps.core.health.responses import DependencyCheck, HealthCheckResponse

__all__ = [
    "HealthCheckResponse",
    "DependencyCheck",
]
