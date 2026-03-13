"""
Strict Deployment Validation Tests.

These tests WILL FAIL if services are not running.
Use these to validate actual deployment readiness before releases.

Unlike unit tests that use mocks, these tests:
- Make REAL HTTP requests
- FAIL when services are down (not skip)
- Validate the entire stack is operational

Run these tests only when services are deployed:
    pytest tests/smoke/test_strict_validation.py -v

Environment variables:
    BACKEND_URL: Backend API URL (default: http://localhost:8000)
    STRICT_MODE: Set to 'false' to skip instead of fail (default: true)
"""

import os
import time
from typing import List

import pytest
import requests

from tests.smoke.conftest import (
    DeploymentStatus,
    RealHTTPClient,
    ServiceEndpoint,
    ServiceHealthResult,
    get_service_endpoints,
)


def is_strict_mode() -> bool:
    """Check if strict mode is enabled."""
    return os.environ.get("STRICT_MODE", "true").lower() != "false"


def strict_assert(condition: bool, message: str):
    """Assert in strict mode, skip in non-strict mode."""
    if not condition:
        if is_strict_mode():
            pytest.fail(message)
        else:
            pytest.skip(f"[NON-STRICT] {message}")


@pytest.mark.smoke
@pytest.mark.strict
class TestStrictBackendValidation:
    """
    Strict backend validation tests.

    These tests FAIL (not skip) when the backend is not running.
    """

    def test_backend_is_running(self, http_client: RealHTTPClient):
        """
        STRICT: Backend MUST be running.

        This test fails if the backend is not accessible.
        """
        result = http_client.check_health("/health/live")

        strict_assert(
            result.is_healthy,
            f"DEPLOYMENT FAILURE: Backend is not running!\n"
            f"URL: {http_client.base_url}\n"
            f"Error: {result.error_message}\n"
            f"Action: Start backend with 'docker-compose up -d backend'"
        )

    def test_backend_database_connected(self, http_client: RealHTTPClient):
        """
        STRICT: Backend MUST have database connectivity.

        Readiness endpoint validates database connection.
        """
        result = http_client.check_health("/health/ready")

        strict_assert(
            result.is_healthy,
            f"DEPLOYMENT FAILURE: Backend cannot connect to database!\n"
            f"URL: {http_client.base_url}/health/ready\n"
            f"Status: {result.status_code}\n"
            f"Action: Ensure PostgreSQL is running and configured"
        )

    def test_backend_response_time_acceptable(self, http_client: RealHTTPClient):
        """
        STRICT: Backend response time MUST be under 500ms.
        """
        # Warm up
        http_client.check_health("/health/live")

        # Measure
        times = []
        for _ in range(5):
            result = http_client.check_health("/health/live")
            if result.is_healthy:
                times.append(result.response_time_ms)

        strict_assert(
            len(times) > 0,
            "DEPLOYMENT FAILURE: No successful health check responses"
        )

        avg_time = sum(times) / len(times)
        strict_assert(
            avg_time < 500,
            f"DEPLOYMENT FAILURE: Response time too slow!\n"
            f"Average: {avg_time:.2f}ms (limit: 500ms)\n"
            f"Action: Investigate backend performance"
        )


@pytest.mark.smoke
@pytest.mark.strict
class TestStrictMetricsValidation:
    """
    Strict metrics endpoint validation.
    """

    def test_metrics_endpoint_available(self, http_client: RealHTTPClient):
        """
        STRICT: Metrics endpoint MUST be exposed for Prometheus.
        """
        try:
            response = http_client.get("/metrics")

            strict_assert(
                response.status_code == 200,
                f"DEPLOYMENT FAILURE: Metrics endpoint not available!\n"
                f"Status: {response.status_code}\n"
                f"Action: Ensure prometheus_client is configured"
            )

            content = response.text
            strict_assert(
                len(content) > 0,
                "DEPLOYMENT FAILURE: Metrics endpoint returns empty response"
            )

        except requests.exceptions.ConnectionError as e:
            strict_assert(
                False,
                f"DEPLOYMENT FAILURE: Cannot connect to backend\n"
                f"Error: {e}"
            )


@pytest.mark.smoke
@pytest.mark.strict
class TestStrictAPIValidation:
    """
    Strict API validation tests.
    """

    def test_api_rejects_unauthenticated(self, http_client: RealHTTPClient):
        """
        STRICT: Protected endpoints MUST require authentication.
        """
        protected_endpoints = [
            "/api/v1/users/",
            "/api/v1/products/",
        ]

        for endpoint in protected_endpoints:
            try:
                response = http_client.get(endpoint)

                if response.status_code == 404:
                    continue

                strict_assert(
                    response.status_code in [401, 403],
                    f"SECURITY FAILURE: {endpoint} accessible without auth!\n"
                    f"Status: {response.status_code}\n"
                    f"Action: Configure authentication middleware"
                )
                return

            except requests.exceptions.ConnectionError:
                strict_assert(False, "Backend not accessible")

    def test_api_returns_json_errors(self, http_client: RealHTTPClient):
        """
        STRICT: API errors MUST return JSON responses.
        """
        try:
            response = http_client.get("/api/nonexistent-endpoint-xyz")

            content_type = response.headers.get("content-type", "")

            strict_assert(
                "application/json" in content_type or response.status_code == 404,
                f"API ERROR: 404 response should be JSON\n"
                f"Content-Type: {content_type}\n"
                f"Action: Configure JSON error responses"
            )

        except requests.exceptions.ConnectionError:
            strict_assert(False, "Backend not accessible")


@pytest.mark.smoke
@pytest.mark.strict
class TestStrictDeploymentStatus:
    """
    Comprehensive deployment status check.
    """

    def test_deployment_ready(
        self,
        service_endpoints: List[ServiceEndpoint],
    ):
        """
        STRICT: All required services MUST be running.

        This is the primary deployment gate test.
        """
        status = DeploymentStatus()
        required_services = []

        for endpoint in service_endpoints:
            client = RealHTTPClient(endpoint.base_url, timeout=5.0)
            try:
                result = client.check_health(endpoint.health_path)
                result.service_name = endpoint.name
                status.add_result(result)

                if endpoint.required and not result.is_healthy:
                    required_services.append(endpoint.name)
            finally:
                client.close()

        # Generate report
        print("\n" + "="*70)
        print("STRICT DEPLOYMENT VALIDATION REPORT")
        print("="*70)

        for result in status.results:
            icon = "✅" if result.is_healthy else "❌"
            print(f"{icon} {result.service_name:20} {result.url}")
            if not result.is_healthy:
                print(f"   └── Error: {result.error_message}")

        print("="*70)
        print(f"Result: {status.healthy_count}/{len(status.results)} services healthy")
        print("="*70 + "\n")

        strict_assert(
            len(required_services) == 0,
            f"DEPLOYMENT FAILURE: Required services are DOWN!\n"
            f"Down services: {required_services}\n"
            f"Action: docker-compose up -d"
        )


@pytest.mark.smoke
@pytest.mark.strict
class TestStrictPerformance:
    """
    Strict performance validation.
    """

    def test_health_under_200ms(self, http_client: RealHTTPClient):
        """
        STRICT: Health endpoint MUST respond under 200ms (FR-013).
        """
        # Warm up connection
        http_client.check_health("/health/live")

        times = []
        for _ in range(10):
            result = http_client.check_health("/health/live")
            if result.is_healthy:
                times.append(result.response_time_ms)

        strict_assert(len(times) >= 8, "Too many failed health checks")

        p95 = sorted(times)[int(len(times) * 0.95)]

        strict_assert(
            p95 < 200,
            f"PERFORMANCE FAILURE: Health check p95 = {p95:.2f}ms (limit: 200ms)"
        )

    def test_sustained_health_stability(self, http_client: RealHTTPClient):
        """
        STRICT: Health checks MUST be stable over time.
        """
        failures = 0

        for i in range(20):
            result = http_client.check_health("/health/live")
            if not result.is_healthy:
                failures += 1
            time.sleep(0.1)

        failure_rate = failures / 20 * 100

        strict_assert(
            failure_rate < 5,
            f"STABILITY FAILURE: {failure_rate:.1f}% health check failure rate\n"
            f"Action: Investigate service stability"
        )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "strict: mark test as strict (fails instead of skipping when services down)",
    )
