"""
Health check endpoint views.

Provides views for Kubernetes-compatible health probes:
- /health/live - Liveness probe
- /health/ready - Readiness probe
- /health/startup - Startup probe

And the combined health check endpoint:
- /api/v1/health/ - Combined health check (DB, cache, migrations)

Per spec.md FR-019 through FR-023 and api-contract.md requirements.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.health.checks import (
    check_cache,
    check_database,
    check_migrations,
    get_pending_migration_count,
)
from apps.core.health.responses import DependencyCheck, HealthCheckResponse

logger = logging.getLogger(__name__)


class LivenessView(APIView):
    """Liveness probe endpoint.

    Returns 200 OK if the process is alive and responsive.
    Does not check any dependencies - just confirms the server is running.

    Kubernetes uses this to know when to restart a container.
    If this fails, the container will be killed and restarted.

    Path: /health/live
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required
    throttle_classes = []  # Exempt from rate limiting (Docker healthchecks)

    @extend_schema(
        operation_id="health_liveness",
        summary="Liveness probe",
        description="Returns 200 if the process is alive. Used by Kubernetes to detect hung processes.",
        tags=["Health Checks"],
        auth=[],  # No authentication required
        responses={
            200: OpenApiResponse(
                description="Process is alive",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy"]},
                    },
                    "example": {"status": "healthy"},
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for liveness probe.

        Args:
            request: The incoming request

        Returns:
            200 OK with {"status": "healthy"}
        """
        response_data = HealthCheckResponse.simple_healthy()
        return Response(response_data.to_dict(), status=status.HTTP_200_OK)


class ReadinessView(APIView):
    """Readiness probe endpoint.

    Returns 200 OK if the application is ready to accept traffic.
    Checks critical dependencies like database connectivity.

    Kubernetes uses this to know when to add/remove the pod from service.
    If this fails, traffic will be routed away from this pod.

    Path: /health/ready
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required
    throttle_classes = []  # Exempt from rate limiting (Docker healthchecks)

    @extend_schema(
        operation_id="health_readiness",
        summary="Readiness probe",
        description="Returns 200 if ready to accept traffic. Checks database connectivity.",
        tags=["Health Checks"],
        auth=[],  # No authentication required
        responses={
            200: OpenApiResponse(
                description="Ready to accept traffic",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                        "checks": {
                            "type": "object",
                            "properties": {
                                "database": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "latency_ms": {"type": "number"},
                                    },
                                },
                            },
                        },
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                    "example": {
                        "status": "healthy",
                        "checks": {"database": {"status": "healthy", "latency_ms": 12.5}},
                        "timestamp": "2025-12-03T10:30:00Z",
                    },
                },
            ),
            503: OpenApiResponse(
                description="Not ready to accept traffic",
                response={
                    "type": "object",
                    "example": {
                        "status": "unhealthy",
                        "checks": {"database": {"status": "unhealthy", "error": "Connection refused"}},
                        "timestamp": "2025-12-03T10:30:00Z",
                    },
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for readiness probe.

        Checks database connectivity and returns appropriate status.

        Args:
            request: The incoming request

        Returns:
            200 OK if all checks pass, 503 Service Unavailable otherwise
        """
        # Perform health checks
        checks = {
            "database": check_database(),
        }

        # Build response
        response_data = HealthCheckResponse.from_checks(checks)

        # Return appropriate HTTP status
        http_status = (
            status.HTTP_200_OK
            if response_data.status == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(response_data.to_dict(), status=http_status)


class StartupView(APIView):
    """Startup probe endpoint.

    Returns 200 OK if the application has completed startup.
    Checks both database connectivity and migration status.

    Kubernetes uses this during container startup. While this probe
    fails, liveness and readiness probes are disabled.

    Path: /health/startup
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required
    throttle_classes = []  # Exempt from rate limiting (Docker healthchecks)

    @extend_schema(
        operation_id="health_startup",
        summary="Startup probe",
        description="Returns 200 if startup is complete. Checks database and migrations.",
        tags=["Health Checks"],
        auth=[],  # No authentication required
        responses={
            200: OpenApiResponse(
                description="Startup complete",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                        "checks": {
                            "type": "object",
                            "properties": {
                                "database": {"type": "object"},
                                "migrations": {"type": "object"},
                            },
                        },
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                    "example": {
                        "status": "healthy",
                        "checks": {
                            "database": {"status": "healthy", "latency_ms": 15.2},
                            "migrations": {"status": "healthy", "latency_ms": 25.8},
                        },
                        "timestamp": "2025-12-03T10:30:00Z",
                    },
                },
            ),
            503: OpenApiResponse(
                description="Startup not complete",
                response={
                    "type": "object",
                    "example": {
                        "status": "unhealthy",
                        "checks": {
                            "database": {"status": "healthy", "latency_ms": 12.5},
                            "migrations": {"status": "unhealthy", "error": "3 pending migrations"},
                        },
                        "timestamp": "2025-12-03T10:30:00Z",
                    },
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for startup probe.

        Checks database connectivity and migration status.

        Args:
            request: The incoming request

        Returns:
            200 OK if startup is complete, 503 Service Unavailable otherwise
        """
        # Perform health checks
        checks = {
            "database": check_database(),
            "migrations": check_migrations(),
        }

        # Build response
        response_data = HealthCheckResponse.from_checks(checks)

        # Return appropriate HTTP status
        http_status = (
            status.HTTP_200_OK
            if response_data.status == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(response_data.to_dict(), status=http_status)


def _dep_to_contract(check: DependencyCheck) -> dict[str, Any]:
    """Convert a DependencyCheck to the api-contract status format.

    Maps internal 'healthy'/'unhealthy' to contract 'up'/'down'.
    """
    result: dict[str, Any] = {
        "status": "up" if check.status == "healthy" else "down",
    }
    if check.latency_ms is not None:
        result["latency_ms"] = round(check.latency_ms, 2)
    if check.error is not None:
        result["error"] = check.error
    return result


def _get_version() -> str:
    """Return application version from settings or fallback."""
    from django.conf import settings

    return getattr(settings, "VERSION", "0.1.2")


class CombinedHealthView(APIView):
    """Combined health check endpoint for Docker/load-balancer probes.

    Checks database, cache, and migration status in a single request.
    Returns 200 if ALL checks pass, 503 if ANY check fails.

    Path: /api/v1/health/
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Exempt from rate limiting (Docker healthchecks)

    @extend_schema(
        operation_id="health_check",
        summary="System health check",
        tags=["health"],
        responses={
            200: OpenApiResponse(
                description="All systems healthy",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy"]},
                        "checks": {
                            "type": "object",
                            "properties": {
                                "database": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "latency_ms": {"type": "number"},
                                    },
                                },
                                "cache": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "latency_ms": {"type": "number"},
                                    },
                                },
                                "migrations": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "pending": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "version": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                    },
                },
            ),
            503: OpenApiResponse(
                description="One or more systems unhealthy",
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for combined health check.

        Checks database connectivity, cache availability, and migration status.
        Returns 200 if all pass, 503 if any fail.

        Args:
            request: The incoming request.

        Returns:
            JSON response with per-check status, version, and timestamp.
        """
        db_check = check_database()
        cache_check = check_cache()
        mig_check = check_migrations()

        # Build per-check contract responses
        db_result = _dep_to_contract(db_check)
        cache_result = _dep_to_contract(cache_check)

        # Migrations use 'pending' count instead of latency_ms
        pending = get_pending_migration_count()
        if mig_check.status == "healthy":
            mig_result: dict[str, Any] = {"status": "up", "pending": max(pending, 0)}
        elif pending == -1:
            mig_result = {"status": "unknown"}
        else:
            mig_result = {"status": "down", "pending": pending}
            if mig_check.error:
                mig_result["error"] = mig_check.error

        all_healthy = (
            db_check.status == "healthy"
            and cache_check.status == "healthy"
            and mig_check.status == "healthy"
        )

        payload: dict[str, Any] = {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": {
                "database": db_result,
                "cache": cache_result,
                "migrations": mig_result,
            },
            "version": _get_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        http_status = (
            status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=http_status)
