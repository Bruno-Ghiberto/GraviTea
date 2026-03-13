"""
Integration tests for health check endpoints.

Tests Kubernetes probe endpoints:
- /health/live - Liveness probe (is the process running)
- /health/ready - Readiness probe (can it serve traffic)
- /health/startup - Startup probe (has initialization completed)

Per spec.md FR-020 health check requirements.
"""

from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework import status
from unittest.mock import patch

from apps.core.health.responses import DependencyCheck


pytestmark = pytest.mark.django_db


class TestLivenessProbe:
    """Tests for /health/live endpoint (Kubernetes liveness probe)."""

    def test_liveness_returns_healthy(self, api_client):
        """Test liveness probe returns healthy status."""
        response = api_client.get("/health/live")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"

    def test_liveness_no_auth_required(self, api_client):
        """Test liveness probe does not require authentication."""
        # No credentials set
        response = api_client.get("/health/live")

        assert response.status_code == status.HTTP_200_OK

    def test_liveness_response_fast(self, api_client):
        """Test liveness probe responds quickly (no external deps)."""
        import time

        start = time.time()
        response = api_client.get("/health/live")
        elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        # Should respond in under 100ms since no external checks
        assert elapsed < 0.1


class TestReadinessProbe:
    """Tests for /health/ready endpoint (Kubernetes readiness probe)."""

    def test_readiness_returns_healthy(self, api_client):
        """Test readiness probe returns healthy status."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"

    def test_readiness_includes_dependency_checks(self, api_client):
        """Test readiness probe includes dependency status."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        assert "checks" in response.data
        # Should include database check
        assert "database" in response.data["checks"]

    def test_readiness_database_check_has_latency(self, api_client):
        """Test database check includes latency measurement."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        db_check = response.data["checks"]["database"]
        assert db_check["status"] == "healthy"
        assert "latency_ms" in db_check
        assert isinstance(db_check["latency_ms"], (int, float))

    def test_readiness_no_auth_required(self, api_client):
        """Test readiness probe does not require authentication."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK

    def test_readiness_returns_unhealthy_when_db_fails(self, api_client):
        """Test readiness probe returns unhealthy when database is unavailable.

        T032: Integration test for /health/ready with unhealthy DB

        Verifies that when the database is unavailable/unhealthy, the readiness
        endpoint returns HTTP 503 with appropriate error details.
        """
        # Mock the database check to fail
        with patch("apps.core.health.views.check_database") as mock_db_check:
            mock_db_check.return_value = DependencyCheck.unhealthy(
                error="Connection refused"
            )
            response = api_client.get("/health/ready")

        # Verify HTTP 503 Service Unavailable
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Verify overall status is unhealthy
        assert response.data["status"] == "unhealthy"

        # Verify database check is included and unhealthy
        assert "checks" in response.data
        assert "database" in response.data["checks"]
        assert response.data["checks"]["database"]["status"] == "unhealthy"

        # Verify error message is included
        assert "error" in response.data["checks"]["database"]
        assert response.data["checks"]["database"]["error"] == "Connection refused"


class TestStartupProbe:
    """Tests for /health/startup endpoint (Kubernetes startup probe)."""

    def test_startup_returns_healthy(self, api_client):
        """Test startup probe returns healthy after initialization."""
        response = api_client.get("/health/startup")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"

    def test_startup_no_auth_required(self, api_client):
        """Test startup probe does not require authentication."""
        response = api_client.get("/health/startup")

        assert response.status_code == status.HTTP_200_OK


class TestHealthResponseFormat:
    """Tests for health response format consistency."""

    def test_healthy_response_structure(self, api_client, health_response_validator):
        """Test healthy response has correct structure."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        health_response_validator(
            response.data,
            expected_status="healthy",
            expect_checks=True,
            expected_checks=["database"],
        )

    def test_health_response_content_type(self, api_client):
        """Test health responses use JSON content type."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response["Content-Type"]

    def test_liveness_minimal_response(self, api_client):
        """Test liveness probe has minimal response for fast checks."""
        response = api_client.get("/health/live")

        assert response.status_code == status.HTTP_200_OK
        # Liveness should be minimal - just status
        assert "status" in response.data
        # May or may not have checks (liveness should be fast)


class TestHealthCheckContract:
    """Contract tests for health check responses."""

    def test_ready_check_includes_required_fields(self, api_client):
        """Test ready check has all required fields per contract."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Required fields
        assert "status" in data
        assert data["status"] in ("healthy", "unhealthy")

        # Checks structure
        if "checks" in data:
            for check_name, check_data in data["checks"].items():
                assert "status" in check_data
                if check_data["status"] == "healthy":
                    assert "latency_ms" in check_data
                elif check_data["status"] == "unhealthy":
                    assert "error" in check_data

    def test_health_endpoints_do_not_return_rfc7807_on_success(self, api_client):
        """Test successful health checks don't use RFC 7807 format."""
        response = api_client.get("/health/ready")

        assert response.status_code == status.HTTP_200_OK
        # Success responses should NOT have RFC 7807 fields
        assert "type" not in response.data
        assert "title" not in response.data
        assert "trace_id" not in response.data


class TestHealthCheckHTTPMethods:
    """Test HTTP methods for health endpoints."""

    def test_live_only_allows_get(self, api_client):
        """Test liveness probe only allows GET."""
        # POST should fail
        response = api_client.post("/health/live")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_ready_only_allows_get(self, api_client):
        """Test readiness probe only allows GET."""
        response = api_client.post("/health/ready")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_startup_only_allows_get(self, api_client):
        """Test startup probe only allows GET."""
        response = api_client.post("/health/startup")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
