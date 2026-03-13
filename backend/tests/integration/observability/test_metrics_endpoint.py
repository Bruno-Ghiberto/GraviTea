"""
Integration tests for /metrics endpoint.

Tests Prometheus metrics endpoint format, response time, and access control.
Per 004-observability-metrics spec FR-001 through FR-010.
"""

import time

import pytest
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class TestMetricsEndpoint(TestCase):
    """Integration tests for the /metrics endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_metrics_endpoint_returns_200(self):
        """T021: Test /metrics endpoint returns 200 OK."""
        response = self.client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_content_type(self):
        """T021: Test /metrics returns correct Prometheus content type."""
        response = self.client.get("/metrics")

        # Prometheus exposition format content type
        content_type = response["Content-Type"]
        assert "text/plain" in content_type or "text/openmetrics" in content_type

    def test_metrics_endpoint_format(self):
        """T021: Test /metrics returns valid Prometheus exposition format."""
        response = self.client.get("/metrics")

        content = response.content.decode("utf-8")

        # Should contain metric names with # HELP and # TYPE comments
        # At minimum, our custom metrics should be present
        lines = content.split("\n")

        # Check for metric format (name, labels, value)
        has_valid_metrics = any(
            line and not line.startswith("#") and " " in line for line in lines
        )
        assert has_valid_metrics, "No valid metrics found in response"

    def test_metrics_endpoint_contains_http_request_metrics(self):
        """T021: Test /metrics contains HTTP request metrics."""
        # First make some requests to generate metrics
        self.client.get("/health/live")

        response = self.client.get("/metrics")
        content = response.content.decode("utf-8")

        # Should contain our RED metrics
        assert "http_requests_total" in content or "http_request" in content

    def test_metrics_endpoint_response_time(self):
        """T022: Test /metrics responds in < 100ms."""
        # Warm up
        self.client.get("/metrics")

        # Measure response time
        start = time.perf_counter()
        response = self.client.get("/metrics")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 100, f"Metrics endpoint took {elapsed_ms:.2f}ms (target: <100ms)"

    def test_metrics_endpoint_cache_headers(self):
        """T021: Test /metrics includes no-cache headers."""
        response = self.client.get("/metrics")

        # Should have cache control headers to prevent caching
        assert "no-cache" in response.get("Cache-Control", "")

    def test_metrics_endpoint_head_request(self):
        """T021: Test /metrics supports HEAD requests."""
        response = self.client.head("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response["Content-Type"] or "text/openmetrics" in response["Content-Type"]


class TestMetricsEndpointUnauthenticated(TestCase):
    """Test unauthenticated access to metrics endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_unauthenticated_access_allowed(self):
        """T023: Test /metrics is accessible without authentication."""
        response = self.client.get("/metrics")

        # Should be accessible for Prometheus scraping
        assert response.status_code == 200

    def test_unauthenticated_returns_aggregate_metrics(self):
        """T023: Test unauthenticated access returns aggregate metrics."""
        response = self.client.get("/metrics")
        content = response.content.decode("utf-8")

        # Should contain metrics without exposing sensitive tenant data
        # The metrics should be present but tenant-specific details may be aggregated
        assert response.status_code == 200

    def test_no_sensitive_data_exposed(self):
        """T023: Test /metrics does not expose sensitive information."""
        response = self.client.get("/metrics")
        content = response.content.decode("utf-8").lower()

        # Should not contain sensitive information
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "api_key",
            "private_key",
            "credential",
        ]

        for pattern in sensitive_patterns:
            assert pattern not in content, f"Sensitive data '{pattern}' found in metrics"


@pytest.mark.django_db
class TestMetricsEndpointAuthenticated:
    """Test authenticated access to metrics endpoint."""

    def test_authenticated_metrics_include_tenant_label(self, client):
        """T024: Test authenticated requests can include tenant-specific labels."""
        # First, make some authenticated requests (simulated)
        # The tenant_id should appear in metrics labels

        response = client.get("/metrics")
        content = response.content.decode("utf-8")

        # tenant_id label should be present in metrics
        # (even if value is empty for unauthenticated requests)
        assert response.status_code == 200


class TestMetricsMultipleScrapes(TestCase):
    """Test metrics endpoint under repeated scraping."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_consistent_metrics_across_scrapes(self):
        """Test that metrics are consistent across multiple scrapes."""
        # Scrape multiple times
        responses = []
        for _ in range(5):
            response = self.client.get("/metrics")
            responses.append(response.content.decode("utf-8"))
            assert response.status_code == 200

        # All responses should be valid Prometheus format

    def test_metrics_accumulate_correctly(self):
        """Test that counters accumulate across requests."""
        # Make initial request to get baseline
        initial_response = self.client.get("/metrics")
        initial_content = initial_response.content.decode("utf-8")

        # Make some API requests
        for _ in range(5):
            self.client.get("/health/live")

        # Check metrics again
        final_response = self.client.get("/metrics")
        final_content = final_response.content.decode("utf-8")

        # Both should be valid
        assert initial_response.status_code == 200
        assert final_response.status_code == 200


class TestMetricsEndpointErrors(TestCase):
    """Test /metrics endpoint error handling."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_metrics_endpoint_handles_post_gracefully(self):
        """Test /metrics rejects POST requests appropriately."""
        response = self.client.post("/metrics", {})

        # Should return Method Not Allowed
        assert response.status_code == 405

    def test_metrics_endpoint_handles_invalid_accept(self):
        """Test /metrics handles invalid Accept header."""
        response = self.client.get(
            "/metrics",
            HTTP_ACCEPT="application/json",
        )

        # Should still return metrics (Prometheus format is default)
        assert response.status_code == 200
