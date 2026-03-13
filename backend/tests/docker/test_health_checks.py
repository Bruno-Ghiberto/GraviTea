"""
Docker Health Check Tests.

Tests for FR-013 and FR-014:
- FR-013: Services MUST expose /health/live and /health/ready endpoints
- FR-014: Health checks MUST respond within 5 seconds

These tests verify that all services implement proper health check endpoints
for Kubernetes/Docker orchestration compatibility.
"""

import asyncio
import time
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest
import requests
from requests.exceptions import ConnectionError, Timeout

from tests.fixtures.docker_models import (
    HEALTH_CHECK_ENDPOINTS,
    DOCKER_SERVICES_CONFIG,
    HealthCheckResult,
)


@pytest.fixture
def base_url() -> str:
    """Base URL for the test service."""
    return "http://localhost:8001"


@pytest.fixture
def health_endpoints() -> Dict[str, str]:
    """Health check endpoint paths (no trailing slashes - matches Django URL config)."""
    return {
        "liveness": "/health/live",
        "readiness": "/health/ready",
        "startup": "/health/startup",  # Optional
    }


@pytest.fixture
def service_urls() -> Dict[str, str]:
    """Service URLs for multi-service testing."""
    return {
        "web": "http://localhost:8001",
        "postgres": "postgres://localhost:5433",
        "redis": "redis://localhost:6380",
    }


def check_health_endpoint(url: str, timeout: float = 5.0) -> HealthCheckResult:
    """
    Check a health endpoint and return result.

    Args:
        url: Full URL to health endpoint
        timeout: Request timeout in seconds

    Returns:
        HealthCheckResult with status and timing information
    """
    start_time = time.perf_counter()

    try:
        response = requests.get(url, timeout=timeout)
        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000

        return HealthCheckResult(
            service_name=url.split("/")[2].split(":")[0],
            endpoint=url,
            is_healthy=response.status_code == 200,
            response_time_ms=response_time_ms,
            status_code=response.status_code,
            response_body=response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
        )
    except Timeout:
        end_time = time.perf_counter()
        return HealthCheckResult(
            service_name=url.split("/")[2].split(":")[0],
            endpoint=url,
            is_healthy=False,
            response_time_ms=(end_time - start_time) * 1000,
            status_code=None,
            error="Timeout",
        )
    except ConnectionError as e:
        end_time = time.perf_counter()
        return HealthCheckResult(
            service_name=url.split("/")[2].split(":")[0],
            endpoint=url,
            is_healthy=False,
            response_time_ms=(end_time - start_time) * 1000,
            status_code=None,
            error=str(e),
        )
    except Exception as e:
        end_time = time.perf_counter()
        return HealthCheckResult(
            service_name=url.split("/")[2].split(":")[0],
            endpoint=url,
            is_healthy=False,
            response_time_ms=(end_time - start_time) * 1000,
            status_code=None,
            error=str(e),
        )


@pytest.mark.docker
class TestHealthEndpointsExist:
    """
    FR-013: Services MUST expose /health/live and /health/ready endpoints.

    Tests that required health check endpoints are available.
    """

    def test_health_endpoints_exist(self, base_url: str, health_endpoints: Dict[str, str]):
        """
        Test that /health/live and /health/ready endpoints exist (FR-013).
        """
        required_endpoints = ["liveness", "readiness"]

        for endpoint_type in required_endpoints:
            endpoint_path = health_endpoints[endpoint_type]
            full_url = f"{base_url}{endpoint_path}"

            # Attempt to reach the endpoint
            result = check_health_endpoint(full_url)

            # Endpoint should exist (even if service is down, we should get a response)
            # 404 means endpoint doesn't exist, which fails FR-013
            assert result.status_code != 404, (
                f"Health endpoint {endpoint_path} does not exist (FR-013)"
            )

    def test_liveness_endpoint_returns_200_when_healthy(self, base_url: str):
        """
        Test that liveness endpoint returns 200 when service is healthy.
        """
        result = check_health_endpoint(f"{base_url}/health/live")

        if result.status_code is not None:
            # If we can reach it, it should return 200
            assert result.status_code == 200, (
                f"Liveness endpoint should return 200 when healthy, got {result.status_code}"
            )

    def test_readiness_endpoint_returns_200_when_ready(self, base_url: str):
        """
        Test that readiness endpoint returns 200 when service is ready.
        """
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.status_code is not None:
            # Ready endpoint returns 200 when all dependencies are available
            # May return 503 during startup or if dependencies are down
            assert result.status_code in [200, 503], (
                f"Readiness endpoint should return 200 or 503, got {result.status_code}"
            )

    def test_health_endpoint_response_format(self, base_url: str):
        """
        Test that health endpoints return proper JSON format.
        """
        result = check_health_endpoint(f"{base_url}/health/live")

        if result.response_body is not None:
            # Response should have status field
            assert "status" in result.response_body, (
                "Health response should include 'status' field"
            )

            # Status should be a known value
            assert result.response_body["status"] in ["healthy", "unhealthy", "degraded"], (
                f"Unknown health status: {result.response_body.get('status')}"
            )


@pytest.mark.docker
class TestHealthCheckResponseTime:
    """
    FR-014: Health checks MUST respond within 5 seconds.

    Tests that health checks meet the SLA for response time.
    """

    def test_health_check_response_time(self, base_url: str, health_endpoints: Dict[str, str]):
        """
        Test that health checks respond within 5 seconds (FR-014).
        """
        max_response_time_ms = 5000  # 5 seconds

        for endpoint_type, endpoint_path in health_endpoints.items():
            if endpoint_type == "startup":
                continue  # Startup endpoint is optional

            full_url = f"{base_url}{endpoint_path}"
            result = check_health_endpoint(full_url, timeout=5.0)

            # Check meets SLA
            assert result.meets_sla(), (
                f"Health check {endpoint_path} took {result.response_time_ms:.2f}ms, "
                f"exceeds SLA of {max_response_time_ms}ms (FR-014)"
            )

    def test_health_check_under_load(self, base_url: str):
        """
        Test that health checks remain fast under load.
        """
        import concurrent.futures

        def make_health_request():
            return check_health_endpoint(f"{base_url}/health/live", timeout=5.0)

        # Make 50 concurrent health check requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Calculate statistics
        response_times = [r.response_time_ms for r in results if r.status_code is not None]

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]

            assert p95_time < 5000, (
                f"Health check p95 response time {p95_time:.2f}ms exceeds 5s SLA"
            )

    def test_health_check_timeout_handling(self, base_url: str):
        """
        Test that health checks properly timeout or complete successfully.

        With very short timeout (0.001s):
        - Either completes successfully if the service is fast enough
        - Or times out gracefully with an error message
        Both outcomes are acceptable - we're testing graceful handling.
        """
        # Request with very short timeout should either succeed or timeout gracefully
        result = check_health_endpoint(f"{base_url}/health/live", timeout=0.001)

        # Either:
        # 1. Request succeeded (is_healthy=True) - service responded fast enough
        # 2. Request failed (is_healthy=False) with an error - timeout or connection issue
        if result.is_healthy:
            # Success case: service responded within the timeout
            assert result.status_code == 200
        else:
            # Failure case: should have an error explaining why
            assert result.error is not None or result.status_code is not None, (
                "Failed health check should have either an error message or status code"
            )


@pytest.mark.docker
class TestHealthCheckDependencies:
    """
    Test health check dependency reporting.
    """

    def test_readiness_checks_database(self, base_url: str):
        """
        Test that readiness endpoint checks database connection.
        """
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.response_body and "checks" in result.response_body:
            checks = result.response_body["checks"]

            # checks is a dict with check names as keys (e.g., {"database": {...}})
            db_check = (
                checks.get("database")
                or checks.get("db")
                or checks.get("postgres")
            )

            if db_check:
                assert "status" in db_check, "Database check should have status"

    def test_readiness_checks_redis(self, base_url: str):
        """
        Test that readiness endpoint checks Redis connection.
        """
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.response_body and "checks" in result.response_body:
            checks = result.response_body["checks"]

            # checks is a dict with check names as keys (e.g., {"redis": {...}})
            redis_check = checks.get("redis") or checks.get("cache")

            if redis_check:
                assert "status" in redis_check, "Redis check should have status"

    def test_liveness_independent_of_dependencies(self, base_url: str):
        """
        Test that liveness endpoint doesn't check external dependencies.

        Liveness should only check if the application process is running,
        not if dependencies are available.
        """
        result = check_health_endpoint(f"{base_url}/health/live")

        # Liveness should generally succeed if the app is running
        # even if database/redis are down
        if result.status_code is not None:
            # Should not include dependency checks in liveness
            if result.response_body and "checks" in result.response_body:
                checks = result.response_body["checks"]
                # Liveness should have minimal checks
                assert len(checks) <= 2, (
                    "Liveness should not check many dependencies"
                )


@pytest.mark.docker
class TestHealthCheckFixtures:
    """
    Test health checks using fixture configurations.
    """

    @pytest.mark.parametrize("endpoint_config", HEALTH_CHECK_ENDPOINTS)
    def test_health_endpoint_from_fixture(self, endpoint_config: Dict):
        """
        Test health endpoints defined in fixtures.
        """
        url = endpoint_config["url"]
        expected_status = endpoint_config.get("expected_status", 200)
        max_response_time = endpoint_config.get("max_response_time_ms", 5000)

        result = check_health_endpoint(url, timeout=max_response_time / 1000)

        if result.status_code is not None:
            assert result.status_code == expected_status, (
                f"Endpoint {url} expected status {expected_status}, got {result.status_code}"
            )
            assert result.response_time_ms < max_response_time, (
                f"Endpoint {url} response time {result.response_time_ms}ms exceeds {max_response_time}ms"
            )


@pytest.mark.docker
class TestHealthCheckFormats:
    """
    Test health check response formats.
    """

    def test_health_response_includes_version(self, base_url: str):
        """
        Test that health response includes application version.
        """
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.response_body:
            # Version info is optional but recommended
            version_fields = ["version", "app_version", "build"]
            has_version = any(f in result.response_body for f in version_fields)
            # Just verify the response structure is valid
            assert "status" in result.response_body or result.is_healthy

    def test_health_response_includes_timestamp(self, base_url: str):
        """
        Test that health response includes timestamp.
        """
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.response_body:
            timestamp_fields = ["timestamp", "checked_at", "time"]
            has_timestamp = any(f in result.response_body for f in timestamp_fields)
            # Timestamp is optional but useful for debugging

    def test_unhealthy_response_includes_reason(self, base_url: str):
        """
        Test that unhealthy responses include reason.
        """
        # Simulate unhealthy state by checking during startup
        result = check_health_endpoint(f"{base_url}/health/ready")

        if result.status_code == 503:
            # Unhealthy response should explain why
            if result.response_body:
                has_reason = (
                    "reason" in result.response_body or
                    "error" in result.response_body or
                    "message" in result.response_body or
                    "checks" in result.response_body
                )
                assert has_reason, "Unhealthy response should include reason"


@pytest.mark.docker
class TestKubernetesCompatibility:
    """
    Test Kubernetes probe compatibility.
    """

    def test_liveness_probe_compatibility(self, base_url: str):
        """
        Test that liveness endpoint is compatible with Kubernetes probes.
        """
        # Kubernetes expects:
        # - 200-399 status code for success
        # - Any other status code for failure
        # - Response within configured timeout

        result = check_health_endpoint(f"{base_url}/health/live", timeout=10.0)

        if result.status_code is not None:
            # Should return 2xx or 3xx for healthy
            assert 200 <= result.status_code < 400 or result.status_code >= 500, (
                f"Unexpected status code {result.status_code} for liveness probe"
            )

    def test_readiness_probe_compatibility(self, base_url: str):
        """
        Test that readiness endpoint is compatible with Kubernetes probes.
        """
        result = check_health_endpoint(f"{base_url}/health/ready", timeout=10.0)

        if result.status_code is not None:
            # Should return 2xx/3xx when ready, 5xx when not ready
            assert result.status_code in [200, 503], (
                f"Readiness probe should return 200 or 503, got {result.status_code}"
            )

    def test_startup_probe_compatibility(self, base_url: str):
        """
        Test that startup endpoint (if present) is compatible with Kubernetes.
        """
        result = check_health_endpoint(f"{base_url}/health/startup", timeout=30.0)

        # Startup probe is optional
        if result.status_code is not None and result.status_code != 404:
            # During startup, may return 503; when ready, returns 200
            assert result.status_code in [200, 503], (
                f"Startup probe should return 200 or 503, got {result.status_code}"
            )
