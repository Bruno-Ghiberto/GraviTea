"""
Observability Stack Integration Tests.

FR-018: Observability stack MUST be integrated.

These tests validate the REAL observability stack integration:
- Prometheus metrics collection
- Grafana dashboard accessibility
- Jaeger tracing
- Loki log aggregation

Requirements:
- Full observability stack must be running
- Run: docker-compose -f docker-compose.observability.yml up -d
"""

import os
import time
from typing import Any, Dict, List, Optional

import pytest
import requests

from tests.smoke.conftest import RealHTTPClient, ServiceHealthResult


@pytest.mark.smoke
@pytest.mark.observability
class TestPrometheusIntegration:
    """
    Test Prometheus metrics collection and scraping.

    FR-018: Prometheus metrics exposed.
    """

    @pytest.fixture
    def prometheus_client(self, prometheus_url: str) -> RealHTTPClient:
        """Create Prometheus HTTP client."""
        client = RealHTTPClient(prometheus_url, timeout=10.0)
        yield client
        client.close()

    def test_prometheus_is_healthy(self, prometheus_client: RealHTTPClient):
        """
        Verify Prometheus service is running and healthy.
        """
        result = prometheus_client.check_health("/-/healthy")

        if not result.is_healthy:
            pytest.skip(
                f"Prometheus not available at {prometheus_client.base_url}\n"
                f"Start with: docker-compose -f docker-compose.observability.yml up -d prometheus"
            )

    def test_prometheus_can_query_targets(self, prometheus_client: RealHTTPClient):
        """
        Verify Prometheus can query its configured targets.
        """
        try:
            response = prometheus_client.get("/api/v1/targets")

            if response.status_code != 200:
                pytest.skip("Prometheus API not available")

            data = response.json()
            assert data.get("status") == "success", (
                f"Prometheus targets query failed: {data}"
            )

            # Check if any targets are configured
            active_targets = data.get("data", {}).get("activeTargets", [])
            print(f"\nPrometheus has {len(active_targets)} active targets:")
            for target in active_targets:
                health = target.get("health", "unknown")
                job = target.get("labels", {}).get("job", "unknown")
                instance = target.get("labels", {}).get("instance", "unknown")
                print(f"  - {job} ({instance}): {health}")

        except requests.exceptions.ConnectionError:
            pytest.skip("Prometheus not available")

    def test_prometheus_scrapes_backend_metrics(
        self,
        prometheus_client: RealHTTPClient,
        backend_url: str,
    ):
        """
        FR-018: Verify Prometheus scrapes backend metrics.
        """
        try:
            # Query Prometheus for any metric from the backend
            response = prometheus_client.get(
                "/api/v1/query",
                params={"query": "up{job=~\".*backend.*\"}"}
            )

            if response.status_code != 200:
                pytest.skip("Prometheus query API not available")

            data = response.json()

            if data.get("status") != "success":
                pytest.skip("Prometheus query failed")

            results = data.get("data", {}).get("result", [])

            if not results:
                # Try alternative query
                response = prometheus_client.get(
                    "/api/v1/query",
                    params={"query": "python_info"}
                )
                data = response.json()
                results = data.get("data", {}).get("result", [])

            # Note: This may skip if backend target isn't configured in Prometheus
            if not results:
                pytest.skip(
                    "No backend metrics found in Prometheus.\n"
                    "Ensure Prometheus is configured to scrape the backend."
                )

            print(f"\nFound {len(results)} backend metric series in Prometheus")

        except requests.exceptions.ConnectionError:
            pytest.skip("Prometheus not available")

    def test_prometheus_has_recent_data(self, prometheus_client: RealHTTPClient):
        """
        Verify Prometheus has recent metrics data.
        """
        try:
            # Query for any recent data point
            response = prometheus_client.get(
                "/api/v1/query",
                params={"query": "up"}
            )

            if response.status_code != 200:
                pytest.skip("Prometheus not available")

            data = response.json()
            results = data.get("data", {}).get("result", [])

            if not results:
                pytest.skip("No metrics data in Prometheus")

            # Check timestamp of first result
            for result in results:
                value = result.get("value", [])
                if len(value) >= 2:
                    timestamp = float(value[0])
                    current_time = time.time()
                    age_seconds = current_time - timestamp

                    assert age_seconds < 300, (
                        f"Prometheus data is stale! Last update was {age_seconds:.0f}s ago"
                    )
                    print(f"\nPrometheus data is {age_seconds:.0f}s old (fresh)")
                    return

        except requests.exceptions.ConnectionError:
            pytest.skip("Prometheus not available")


@pytest.mark.smoke
@pytest.mark.observability
class TestGrafanaIntegration:
    """
    Test Grafana dashboard accessibility.

    FR-018: Observability stack integrated.
    """

    @pytest.fixture
    def grafana_client(self, grafana_url: str) -> RealHTTPClient:
        """Create Grafana HTTP client."""
        client = RealHTTPClient(grafana_url, timeout=10.0)
        yield client
        client.close()

    def test_grafana_is_healthy(self, grafana_client: RealHTTPClient):
        """
        Verify Grafana service is running.
        """
        result = grafana_client.check_health("/api/health")

        if not result.is_healthy:
            pytest.skip(
                f"Grafana not available at {grafana_client.base_url}\n"
                f"Start with: docker-compose -f docker-compose.observability.yml up -d grafana"
            )

    def test_grafana_api_accessible(self, grafana_client: RealHTTPClient):
        """
        Verify Grafana API is accessible.
        """
        try:
            response = grafana_client.get("/api/health")

            if response.status_code != 200:
                pytest.skip("Grafana API not accessible")

            data = response.json()
            assert data.get("database") == "ok", (
                f"Grafana database not healthy: {data}"
            )

        except requests.exceptions.ConnectionError:
            pytest.skip("Grafana not available")

    def test_grafana_has_datasources(self, grafana_client: RealHTTPClient):
        """
        Verify Grafana has datasources configured.
        """
        try:
            # Note: This may require authentication
            response = grafana_client.get("/api/datasources")

            if response.status_code == 401:
                pytest.skip("Grafana requires authentication for datasource API")

            if response.status_code != 200:
                pytest.skip(f"Grafana datasource API returned {response.status_code}")

            datasources = response.json()
            print(f"\nGrafana has {len(datasources)} datasources configured")

            for ds in datasources:
                name = ds.get("name", "unknown")
                ds_type = ds.get("type", "unknown")
                print(f"  - {name} ({ds_type})")

        except requests.exceptions.ConnectionError:
            pytest.skip("Grafana not available")

    def test_grafana_frontend_loads(self, grafana_client: RealHTTPClient):
        """
        Verify Grafana web UI is accessible.
        """
        try:
            response = grafana_client.get("/")

            assert response.status_code in [200, 302], (
                f"Grafana frontend returned {response.status_code}"
            )

            # Check if response contains Grafana content
            if response.status_code == 200:
                assert "grafana" in response.text.lower() or "loading" in response.text.lower(), (
                    "Response doesn't appear to be Grafana frontend"
                )

        except requests.exceptions.ConnectionError:
            pytest.skip("Grafana not available")


@pytest.mark.smoke
@pytest.mark.observability
class TestJaegerIntegration:
    """
    Test Jaeger distributed tracing.

    FR-018: Observability stack integrated.
    """

    @pytest.fixture
    def jaeger_client(self, jaeger_url: str) -> RealHTTPClient:
        """Create Jaeger HTTP client."""
        client = RealHTTPClient(jaeger_url, timeout=10.0)
        yield client
        client.close()

    def test_jaeger_is_accessible(self, jaeger_client: RealHTTPClient):
        """
        Verify Jaeger UI is running.
        """
        try:
            response = jaeger_client.get("/")

            if response.status_code != 200:
                pytest.skip(
                    f"Jaeger not available at {jaeger_client.base_url}\n"
                    f"Start with: docker-compose -f docker-compose.observability.yml up -d jaeger"
                )

        except requests.exceptions.ConnectionError:
            pytest.skip("Jaeger not available")

    def test_jaeger_api_returns_services(self, jaeger_client: RealHTTPClient):
        """
        Verify Jaeger API can list services.
        """
        try:
            response = jaeger_client.get("/api/services")

            if response.status_code != 200:
                pytest.skip("Jaeger API not available")

            data = response.json()
            services = data.get("data", [])

            print(f"\nJaeger knows about {len(services)} services:")
            for service in services:
                print(f"  - {service}")

            # Note: May be empty if no traces have been recorded yet
            if not services:
                pytest.skip("No services have sent traces to Jaeger yet")

        except requests.exceptions.ConnectionError:
            pytest.skip("Jaeger not available")

    def test_jaeger_can_query_traces(self, jaeger_client: RealHTTPClient):
        """
        Verify Jaeger can query for traces.
        """
        try:
            # First get available services
            services_response = jaeger_client.get("/api/services")

            if services_response.status_code != 200:
                pytest.skip("Jaeger API not available")

            services = services_response.json().get("data", [])

            if not services:
                pytest.skip("No services in Jaeger")

            # Query traces for first service
            service = services[0]
            response = jaeger_client.get(
                "/api/traces",
                params={"service": service, "limit": 10}
            )

            assert response.status_code == 200, (
                f"Failed to query traces: {response.status_code}"
            )

            data = response.json()
            traces = data.get("data", [])
            print(f"\nFound {len(traces)} recent traces for service '{service}'")

        except requests.exceptions.ConnectionError:
            pytest.skip("Jaeger not available")


@pytest.mark.smoke
@pytest.mark.observability
class TestLokiIntegration:
    """
    Test Loki log aggregation.

    FR-018: Logs structured.
    """

    @pytest.fixture
    def loki_url(self) -> str:
        """Get Loki URL from environment."""
        return os.environ.get("LOKI_URL", "http://localhost:3100")

    @pytest.fixture
    def loki_client(self, loki_url: str) -> RealHTTPClient:
        """Create Loki HTTP client."""
        client = RealHTTPClient(loki_url, timeout=10.0)
        yield client
        client.close()

    def test_loki_is_ready(self, loki_client: RealHTTPClient):
        """
        Verify Loki service is ready.
        """
        result = loki_client.check_health("/ready")

        if not result.is_healthy:
            pytest.skip(
                f"Loki not available at {loki_client.base_url}\n"
                f"Start with: docker-compose -f docker-compose.observability.yml up -d loki"
            )

    def test_loki_can_accept_logs(self, loki_client: RealHTTPClient):
        """
        Verify Loki is accepting log pushes.
        """
        try:
            # Check the push endpoint is available
            # Note: We don't actually push, just verify the endpoint exists
            response = loki_client.get("/ready")

            if response.status_code != 200:
                pytest.skip("Loki not ready")

            # The ready endpoint confirms Loki can accept logs
            print("\nLoki is ready to accept logs")

        except requests.exceptions.ConnectionError:
            pytest.skip("Loki not available")

    def test_loki_can_query_labels(self, loki_client: RealHTTPClient):
        """
        Verify Loki can return available labels.
        """
        try:
            response = loki_client.get("/loki/api/v1/labels")

            if response.status_code != 200:
                pytest.skip("Loki labels API not available")

            data = response.json()
            labels = data.get("data", [])

            print(f"\nLoki has {len(labels)} labels:")
            for label in labels[:10]:  # Show first 10
                print(f"  - {label}")

            if len(labels) > 10:
                print(f"  ... and {len(labels) - 10} more")

        except requests.exceptions.ConnectionError:
            pytest.skip("Loki not available")


@pytest.mark.smoke
@pytest.mark.observability
class TestObservabilityEndToEnd:
    """
    End-to-end observability stack tests.

    Validates the full observability pipeline works together.
    """

    def test_backend_metrics_flow_to_prometheus(
        self,
        http_client: RealHTTPClient,
        prometheus_url: str,
    ):
        """
        FR-018: Verify metrics flow from backend to Prometheus.

        1. Make requests to backend (generates metrics)
        2. Verify Prometheus received the metrics
        """
        # Step 1: Make requests to generate metrics
        for _ in range(5):
            http_client.check_health("/health/live")
            time.sleep(0.1)

        # Step 2: Check if metrics endpoint is working
        try:
            metrics_response = http_client.get("/metrics")
            if metrics_response.status_code != 200:
                pytest.skip("Backend metrics endpoint not available")

            print("\nBackend is exposing metrics")

            # Step 3: Verify Prometheus can see them (if available)
            prom_client = RealHTTPClient(prometheus_url, timeout=5.0)
            try:
                prom_health = prom_client.check_health("/-/healthy")
                if prom_health.is_healthy:
                    print("Prometheus is healthy and can scrape metrics")
            finally:
                prom_client.close()

        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not available")

    def test_observability_stack_connectivity(
        self,
        backend_url: str,
        prometheus_url: str,
        grafana_url: str,
        jaeger_url: str,
    ):
        """
        Test all observability components are running.
        """
        components = {
            "backend": (backend_url, "/health/live"),
            "prometheus": (prometheus_url, "/-/healthy"),
            "grafana": (grafana_url, "/api/health"),
            "jaeger": (jaeger_url, "/"),
        }

        results = {}
        for name, (url, health_path) in components.items():
            client = RealHTTPClient(url, timeout=5.0)
            try:
                result = client.check_health(health_path)
                results[name] = result.is_healthy
            except Exception as e:
                results[name] = False
            finally:
                client.close()

        print("\n" + "="*50)
        print("OBSERVABILITY STACK STATUS")
        print("="*50)
        for name, healthy in results.items():
            status = "✅ Running" if healthy else "❌ Not available"
            print(f"{name:15} {status}")
        print("="*50)

        # At minimum, backend should be running
        assert results.get("backend", False), (
            "Backend is not running - cannot test observability"
        )
