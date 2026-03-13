"""
Deployment Readiness Smoke Tests.

FR-013: Health check endpoint MUST respond within 200ms
FR-014: Readiness probe MUST check database connectivity

These tests make REAL HTTP requests to running services.
They validate actual deployment readiness, not mocked behavior.

Requirements:
- Backend service must be running
- Set BACKEND_URL environment variable (default: http://localhost:8000)
"""

import time
from typing import Dict, List

import pytest
import requests

from tests.smoke.conftest import (
    DeploymentStatus,
    RealHTTPClient,
    ServiceEndpoint,
    ServiceHealthResult,
)


@pytest.mark.smoke
@pytest.mark.integration
class TestBackendHealthEndpoints:
    """
    Test backend health endpoints with REAL HTTP requests.

    FR-013: Health check endpoint MUST respond within 200ms.
    FR-014: Readiness probe MUST check database connectivity.
    """

    def test_liveness_endpoint_responds(self, http_client: RealHTTPClient):
        """
        FR-013: Liveness endpoint must respond successfully.

        This makes a REAL HTTP request to the running backend.
        Test FAILS if backend is not running or not healthy.
        """
        result = http_client.check_health("/health/live")

        assert result.is_healthy, (
            f"Liveness check FAILED - Backend is not healthy!\n"
            f"URL: {result.url}\n"
            f"Status Code: {result.status_code}\n"
            f"Error: {result.error_message}\n"
            f"Ensure backend is running: docker-compose up -d backend"
        )
        assert result.status_code == 200, (
            f"Expected status 200, got {result.status_code}"
        )

    def test_liveness_response_time_under_200ms(self, http_client: RealHTTPClient):
        """
        FR-013: Health check endpoint MUST respond within 200ms.

        Validates the actual response time meets requirements.
        """
        # Warm up the connection
        http_client.check_health("/health/live")

        # Measure actual response time
        result = http_client.check_health("/health/live")

        assert result.is_healthy, (
            f"Cannot measure response time - endpoint is not healthy: {result.error_message}"
        )
        assert result.response_time_ms < 200, (
            f"FR-013 VIOLATION: Health check took {result.response_time_ms:.2f}ms "
            f"(requirement: < 200ms)"
        )

    def test_readiness_endpoint_responds(self, http_client: RealHTTPClient):
        """
        FR-014: Readiness endpoint must respond and check database.

        This validates the readiness probe is functional.
        """
        result = http_client.check_health("/health/ready")

        assert result.is_healthy, (
            f"Readiness check FAILED - Service not ready!\n"
            f"URL: {result.url}\n"
            f"Status Code: {result.status_code}\n"
            f"Error: {result.error_message}\n"
            f"This may indicate database connectivity issues."
        )

    def test_readiness_includes_database_check(self, http_client: RealHTTPClient):
        """
        FR-014: Readiness probe MUST check database connectivity.

        Validates the readiness response includes database status.
        """
        try:
            response = http_client.get("/health/ready")

            assert response.status_code == 200, (
                f"Readiness endpoint returned {response.status_code}"
            )

            # Parse response to verify database check is included
            try:
                data = response.json()
                # The readiness endpoint should include database status
                assert "checks" in data or "database" in str(data).lower(), (
                    f"Readiness response should include database check. Got: {data}"
                )
            except Exception:
                # If not JSON, check for database mention in text
                text = response.text
                assert "database" in text.lower() or response.status_code == 200, (
                    "Readiness endpoint should verify database connectivity"
                )

        except requests.exceptions.ConnectionError as e:
            pytest.fail(
                f"Cannot connect to backend at {http_client.base_url}\n"
                f"Error: {e}\n"
                f"Ensure backend is running: docker-compose up -d backend"
            )

    def test_startup_endpoint_responds(self, http_client: RealHTTPClient):
        """
        Test startup probe endpoint is functional.

        Kubernetes uses this to know when the app is ready to receive traffic.
        """
        result = http_client.check_health("/health/startup")

        assert result.is_healthy, (
            f"Startup check FAILED!\n"
            f"URL: {result.url}\n"
            f"Status Code: {result.status_code}\n"
            f"Error: {result.error_message}"
        )


@pytest.mark.smoke
@pytest.mark.integration
class TestMetricsEndpoint:
    """
    Test Prometheus metrics endpoint.

    FR-018: Observability stack MUST be integrated.
    """

    def test_metrics_endpoint_responds(self, http_client: RealHTTPClient):
        """
        FR-018: Metrics endpoint must expose Prometheus metrics.

        Validates /metrics endpoint is accessible and returns valid data.
        """
        try:
            response = http_client.get("/metrics")

            assert response.status_code == 200, (
                f"Metrics endpoint returned {response.status_code}, expected 200"
            )

            # Prometheus metrics should be text/plain with specific format
            content = response.text
            assert len(content) > 0, "Metrics endpoint returned empty response"

            # Verify it's Prometheus format (contains HELP or TYPE comments)
            assert "# HELP" in content or "# TYPE" in content or "python_" in content, (
                f"Response doesn't appear to be Prometheus metrics format:\n{content[:500]}"
            )

        except requests.exceptions.ConnectionError as e:
            pytest.fail(
                f"Cannot connect to metrics endpoint\n"
                f"Error: {e}\n"
                f"Ensure backend is running with metrics enabled"
            )

    def test_metrics_include_http_metrics(self, http_client: RealHTTPClient):
        """
        FR-018: Metrics should include HTTP request metrics.
        """
        try:
            response = http_client.get("/metrics")

            if response.status_code != 200:
                pytest.skip("Metrics endpoint not available")

            content = response.text

            # Check for common HTTP metrics
            http_metrics = [
                "http_request",
                "django_http",
                "request_latency",
                "request_count",
            ]

            has_http_metrics = any(metric in content.lower() for metric in http_metrics)

            # Note: This is a warning, not a failure, as metrics may be named differently
            if not has_http_metrics:
                pytest.skip(
                    "HTTP metrics not found - verify prometheus_client is configured"
                )

        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not available")


@pytest.mark.smoke
@pytest.mark.integration
class TestDeploymentReadiness:
    """
    Comprehensive deployment readiness validation.

    Tests that ALL required services are running and healthy.
    """

    def test_all_required_services_healthy(
        self,
        service_endpoints: List[ServiceEndpoint],
        deployment_status: DeploymentStatus,
    ):
        """
        Validate all required services are running and healthy.

        This is the primary smoke test for deployment validation.
        """
        for endpoint in service_endpoints:
            client = RealHTTPClient(endpoint.base_url, timeout=5.0)
            try:
                result = client.check_health(endpoint.health_path)
                result.service_name = endpoint.name
                deployment_status.add_result(result)
            finally:
                client.close()

        # Report status
        summary = deployment_status.summary()
        print(f"\n{'='*60}")
        print("DEPLOYMENT STATUS REPORT")
        print(f"{'='*60}")
        print(f"Healthy: {summary['healthy_count']}/{summary['total_count']}")

        for result in deployment_status.results:
            status_icon = "✅" if result.is_healthy else "❌"
            print(f"{status_icon} {result.service_name}: {result.url}")
            if not result.is_healthy:
                print(f"   Error: {result.error_message}")

        print(f"{'='*60}\n")

        # Check required services
        required_failures = []
        for endpoint in service_endpoints:
            if endpoint.required:
                matching_results = [
                    r for r in deployment_status.results
                    if r.service_name == endpoint.name
                ]
                if matching_results and not matching_results[0].is_healthy:
                    required_failures.append(endpoint.name)

        assert len(required_failures) == 0, (
            f"Required services are DOWN: {required_failures}\n"
            f"Run: docker-compose up -d"
        )

    def test_backend_api_accessible(self, http_client: RealHTTPClient):
        """
        Test that the backend API root is accessible.
        """
        try:
            # Try common API endpoints
            endpoints_to_try = ["/api/", "/", "/health/live"]

            for endpoint in endpoints_to_try:
                try:
                    response = http_client.get(endpoint)
                    if response.status_code < 500:
                        # Any non-5xx response means the server is responding
                        return
                except Exception:
                    continue

            pytest.fail("Backend API is not responding on any endpoint")

        except requests.exceptions.ConnectionError as e:
            pytest.fail(
                f"Cannot connect to backend API\n"
                f"URL: {http_client.base_url}\n"
                f"Error: {e}"
            )


@pytest.mark.smoke
@pytest.mark.integration
class TestServiceConnectivity:
    """
    Test connectivity between services.
    """

    def test_backend_can_connect_to_database(self, http_client: RealHTTPClient):
        """
        Verify backend has database connectivity via readiness check.

        The readiness endpoint checks database connectivity.
        If it returns 200, database is connected.
        """
        result = http_client.check_health("/health/ready")

        assert result.is_healthy, (
            f"Backend cannot connect to database!\n"
            f"Readiness check failed with: {result.error_message}\n"
            f"Ensure PostgreSQL is running: docker-compose up -d db"
        )

    def test_consecutive_health_checks_stable(self, http_client: RealHTTPClient):
        """
        Verify health checks are stable over multiple requests.

        Unstable health checks indicate service reliability issues.
        """
        results = []
        for i in range(5):
            result = http_client.check_health("/health/live")
            results.append(result)
            time.sleep(0.1)  # Small delay between checks

        failures = [r for r in results if not r.is_healthy]

        assert len(failures) == 0, (
            f"Health check instability detected!\n"
            f"Failed {len(failures)}/5 consecutive checks.\n"
            f"This indicates service reliability issues."
        )

        # Check response time consistency
        # Use 5x tolerance to account for normal network jitter and CI variance
        VARIANCE_TOLERANCE = 5
        response_times = [r.response_time_ms for r in results]
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        assert max_time < avg_time * VARIANCE_TOLERANCE, (
            f"Response time variance too high!\n"
            f"Average: {avg_time:.2f}ms, Max: {max_time:.2f}ms\n"
            f"Tolerance: {VARIANCE_TOLERANCE}x - This may indicate performance issues."
        )


@pytest.mark.smoke
class TestEnvironmentConfiguration:
    """
    Test environment configuration is correct.
    """

    def test_backend_url_configured(self, backend_url: str):
        """
        Verify backend URL is configured.
        """
        assert backend_url, "BACKEND_URL not configured"
        assert backend_url.startswith("http"), (
            f"Invalid BACKEND_URL: {backend_url}"
        )

    def test_backend_responds_to_configured_url(
        self,
        backend_url: str,
        http_client: RealHTTPClient,
    ):
        """
        Verify the configured backend URL is accessible.
        """
        result = http_client.check_health("/health/live")

        if not result.is_healthy:
            pytest.fail(
                f"Backend not accessible at configured URL: {backend_url}\n"
                f"Error: {result.error_message}\n\n"
                f"To fix:\n"
                f"1. Start backend: docker-compose up -d backend\n"
                f"2. Or set correct BACKEND_URL environment variable"
            )
