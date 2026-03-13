"""
Tests for the combined health check endpoint at /api/v1/health/.

Verifies:
- 200 when all services (DB, cache, migrations) are up
- 503 when database is down
- 503 when cache is down
- Response schema matches api-contract.md
- No authentication required
- Individual check statuses: up, down, unknown

Per tasks.md T015 — test-first for Constitution Principle X.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

HEALTH_URL = "/api/v1/health/"


@pytest.fixture
def client() -> APIClient:
    """Unauthenticated API client for health checks."""
    return APIClient()


class TestHealthEndpointSchema:
    """Verify response schema matches api-contract.md."""

    @pytest.mark.django_db
    def test_returns_200_when_all_healthy(self, client: APIClient) -> None:
        """Health endpoint returns 200 with correct schema when all services up."""
        response = client.get(HEALTH_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Top-level fields
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "version" in data
        assert "timestamp" in data

        # Check sub-objects exist
        assert "database" in data["checks"]
        assert "cache" in data["checks"]
        assert "migrations" in data["checks"]

        # Database check fields
        db = data["checks"]["database"]
        assert db["status"] == "up"
        assert "latency_ms" in db
        assert isinstance(db["latency_ms"], (int, float))

        # Cache check fields
        cache = data["checks"]["cache"]
        assert cache["status"] == "up"
        assert "latency_ms" in cache
        assert isinstance(cache["latency_ms"], (int, float))

        # Migrations check fields
        migrations = data["checks"]["migrations"]
        assert migrations["status"] == "up"
        assert "pending" in migrations
        assert migrations["pending"] == 0

    @pytest.mark.django_db
    def test_timestamp_is_iso8601(self, client: APIClient) -> None:
        """Timestamp field is valid ISO 8601."""
        from datetime import datetime

        response = client.get(HEALTH_URL)
        data = response.json()

        # Should parse without error
        ts = datetime.fromisoformat(data["timestamp"])
        assert ts is not None

    @pytest.mark.django_db
    def test_version_is_string(self, client: APIClient) -> None:
        """Version field is a non-empty string."""
        response = client.get(HEALTH_URL)
        data = response.json()

        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    @pytest.mark.django_db
    def test_response_content_type_json(self, client: APIClient) -> None:
        """Response Content-Type is application/json."""
        response = client.get(HEALTH_URL)
        assert response["Content-Type"] == "application/json"


class TestHealthEndpointNoAuth:
    """Verify no authentication is required."""

    @pytest.mark.django_db
    def test_unauthenticated_access_returns_200(self, client: APIClient) -> None:
        """Health endpoint accessible without JWT token."""
        response = client.get(HEALTH_URL)
        # Should NOT return 401 or 403
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)

    @pytest.mark.django_db
    def test_no_auth_header_required(self, client: APIClient) -> None:
        """No Authorization header needed."""
        response = client.get(HEALTH_URL, HTTP_AUTHORIZATION="")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)


class TestHealthEndpointDatabaseDown:
    """Verify 503 when database is down."""

    @pytest.mark.django_db
    def test_returns_503_when_db_down(self, client: APIClient) -> None:
        """Returns 503 with database status 'down' when DB check fails."""
        with patch(
            "apps.core.health.views.check_database"
        ) as mock_db:
            from apps.core.health.responses import DependencyCheck
            mock_db.return_value = DependencyCheck.unhealthy("connection refused")

            response = client.get(HEALTH_URL)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "down"
        assert "error" in data["checks"]["database"]

    @pytest.mark.django_db
    def test_db_down_still_includes_other_checks(self, client: APIClient) -> None:
        """When DB is down, cache and migration checks still present."""
        with patch(
            "apps.core.health.views.check_database"
        ) as mock_db:
            from apps.core.health.responses import DependencyCheck
            mock_db.return_value = DependencyCheck.unhealthy("connection refused")

            response = client.get(HEALTH_URL)

        data = response.json()
        # Other checks should still be present
        assert "cache" in data["checks"]
        assert "migrations" in data["checks"]


class TestHealthEndpointCacheDown:
    """Verify 503 when cache is down."""

    @pytest.mark.django_db
    def test_returns_503_when_cache_down(self, client: APIClient) -> None:
        """Returns 503 with cache status 'down' when cache check fails."""
        with patch(
            "apps.core.health.views.check_cache"
        ) as mock_cache:
            from apps.core.health.responses import DependencyCheck
            mock_cache.return_value = DependencyCheck.unhealthy("cache connection refused")

            response = client.get(HEALTH_URL)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["cache"]["status"] == "down"


class TestHealthEndpointMigrationsDown:
    """Verify 503 when migrations are pending."""

    @pytest.mark.django_db
    def test_returns_503_when_migrations_pending(self, client: APIClient) -> None:
        """Returns 503 when migrations check reports pending migrations."""
        with patch(
            "apps.core.health.views.check_migrations"
        ) as mock_mig:
            from apps.core.health.responses import DependencyCheck
            mock_mig.return_value = DependencyCheck.unhealthy("3 pending migrations")

            response = client.get(HEALTH_URL)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"

    @pytest.mark.django_db
    def test_migrations_unknown_when_check_fails(self, client: APIClient) -> None:
        """Migrations status is 'unknown' when DB is down and migrations can't be checked."""
        with patch(
            "apps.core.health.views.check_database"
        ) as mock_db, patch(
            "apps.core.health.views.check_migrations"
        ) as mock_mig:
            from apps.core.health.responses import DependencyCheck
            mock_db.return_value = DependencyCheck.unhealthy("connection refused")
            mock_mig.return_value = DependencyCheck.unhealthy("Migration check error: connection refused")

            response = client.get(HEALTH_URL)

        data = response.json()
        assert data["status"] == "unhealthy"
        # When migration check fails due to DB down, status should reflect that
        mig_status = data["checks"]["migrations"]["status"]
        assert mig_status in ("down", "unknown")


class TestHealthEndpointStatusValues:
    """Verify individual check status values follow the contract."""

    @pytest.mark.django_db
    def test_healthy_statuses_are_up(self, client: APIClient) -> None:
        """When all healthy, individual statuses should be 'up' not 'healthy'."""
        response = client.get(HEALTH_URL)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            for check_name, check_data in data["checks"].items():
                assert check_data["status"] == "up", (
                    f"Check '{check_name}' status should be 'up', got '{check_data['status']}'"
                )

    @pytest.mark.django_db
    def test_unhealthy_statuses_are_down(self, client: APIClient) -> None:
        """When a check fails, its status should be 'down' not 'unhealthy'."""
        with patch(
            "apps.core.health.views.check_database"
        ) as mock_db:
            from apps.core.health.responses import DependencyCheck
            mock_db.return_value = DependencyCheck.unhealthy("connection refused")

            response = client.get(HEALTH_URL)

        data = response.json()
        assert data["checks"]["database"]["status"] == "down"


class TestHealthEndpointHTTPMethods:
    """Verify only GET is allowed."""

    @pytest.mark.django_db
    def test_post_not_allowed(self, client: APIClient) -> None:
        """POST to health endpoint is not allowed."""
        response = client.post(HEALTH_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @pytest.mark.django_db
    def test_put_not_allowed(self, client: APIClient) -> None:
        """PUT to health endpoint is not allowed."""
        response = client.put(HEALTH_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @pytest.mark.django_db
    def test_delete_not_allowed(self, client: APIClient) -> None:
        """DELETE to health endpoint is not allowed."""
        response = client.delete(HEALTH_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
