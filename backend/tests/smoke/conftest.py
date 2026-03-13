"""
Smoke Test Fixtures and Configuration.

Provides fixtures for real HTTP integration testing against running services.
These tests require actual services to be running (not mocked).
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ServiceEndpoint:
    """Configuration for a service endpoint."""

    name: str
    base_url: str
    health_path: str = "/health/live"
    timeout: float = 10.0
    required: bool = True

    @property
    def health_url(self) -> str:
        """Return full health check URL."""
        return urljoin(self.base_url, self.health_path)


@dataclass
class ServiceHealthResult:
    """Result of a service health check."""

    service_name: str
    url: str
    is_healthy: bool
    status_code: Optional[int] = None
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "service": self.service_name,
            "url": self.url,
            "healthy": self.is_healthy,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 2),
            "error": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DeploymentStatus:
    """Overall deployment health status."""

    results: List[ServiceHealthResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_result(self, result: ServiceHealthResult) -> None:
        """Add a health check result."""
        self.results.append(result)

    @property
    def all_healthy(self) -> bool:
        """Check if all services are healthy."""
        return all(r.is_healthy for r in self.results)

    @property
    def healthy_count(self) -> int:
        """Count of healthy services."""
        return sum(1 for r in self.results if r.is_healthy)

    @property
    def unhealthy_services(self) -> List[str]:
        """List of unhealthy service names."""
        return [r.service_name for r in self.results if not r.is_healthy]

    def summary(self) -> Dict[str, Any]:
        """Generate deployment summary."""
        return {
            "all_healthy": self.all_healthy,
            "healthy_count": self.healthy_count,
            "total_count": len(self.results),
            "unhealthy_services": self.unhealthy_services,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp.isoformat(),
        }


class RealHTTPClient:
    """
    HTTP client for real service integration testing.

    Unlike Django's TestClient, this makes actual HTTP requests
    to running services, validating true deployment readiness.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = self._create_session(retries, backoff_factor)

    def _create_session(self, retries: int, backoff_factor: float) -> requests.Session:
        """Create a session with retry configuration."""
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Make a GET request."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        return self.session.get(
            url,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make a POST request."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        return self.session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=self.timeout,
        )

    def check_health(self, path: str = "/health/live") -> ServiceHealthResult:
        """Check service health endpoint."""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        start_time = time.time()

        try:
            response = self.get(path)
            elapsed_ms = (time.time() - start_time) * 1000

            return ServiceHealthResult(
                service_name=self.base_url,
                url=url,
                is_healthy=response.status_code == 200,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )
        except requests.exceptions.ConnectionError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ServiceHealthResult(
                service_name=self.base_url,
                url=url,
                is_healthy=False,
                response_time_ms=elapsed_ms,
                error_message=f"Connection failed: {str(e)}",
            )
        except requests.exceptions.Timeout as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ServiceHealthResult(
                service_name=self.base_url,
                url=url,
                is_healthy=False,
                response_time_ms=elapsed_ms,
                error_message=f"Request timed out: {str(e)}",
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ServiceHealthResult(
                service_name=self.base_url,
                url=url,
                is_healthy=False,
                response_time_ms=elapsed_ms,
                error_message=f"Unexpected error: {str(e)}",
            )

    def close(self) -> None:
        """Close the session."""
        self.session.close()


def get_service_endpoints() -> List[ServiceEndpoint]:
    """
    Get configured service endpoints from environment.

    Environment variables:
    - BACKEND_URL: Backend API URL (default: http://localhost:8000)
    - PROMETHEUS_URL: Prometheus URL (default: http://localhost:9090)
    - GRAFANA_URL: Grafana URL (default: http://localhost:3000)
    - JAEGER_URL: Jaeger URL (default: http://localhost:16686)
    - LOKI_URL: Loki URL (default: http://localhost:3100)
    """
    return [
        ServiceEndpoint(
            name="backend",
            # Default to port 8001 to match docker-compose.test.yml web-test mapping
            base_url=os.environ.get("BACKEND_URL", "http://localhost:8001"),
            health_path="/health/live",
            required=True,
        ),
        ServiceEndpoint(
            name="prometheus",
            # Default to port 9091 to match docker-compose.test.yml prometheus-test mapping
            base_url=os.environ.get("PROMETHEUS_URL", "http://localhost:9091"),
            health_path="/-/healthy",
            required=False,
        ),
        ServiceEndpoint(
            name="grafana",
            base_url=os.environ.get("GRAFANA_URL", "http://localhost:3000"),
            health_path="/api/health",
            required=False,
        ),
        ServiceEndpoint(
            name="jaeger",
            base_url=os.environ.get("JAEGER_URL", "http://localhost:16686"),
            health_path="/",
            required=False,
        ),
        ServiceEndpoint(
            name="loki",
            base_url=os.environ.get("LOKI_URL", "http://localhost:3100"),
            health_path="/ready",
            required=False,
        ),
    ]


@pytest.fixture
def backend_url() -> str:
    """Provide backend URL from environment."""
    # Default to port 8001 to match docker-compose.test.yml web-test mapping
    return os.environ.get("BACKEND_URL", "http://localhost:8001")


@pytest.fixture
def prometheus_url() -> str:
    """Provide Prometheus URL from environment."""
    return os.environ.get("PROMETHEUS_URL", "http://localhost:9090")


@pytest.fixture
def grafana_url() -> str:
    """Provide Grafana URL from environment."""
    return os.environ.get("GRAFANA_URL", "http://localhost:3000")


@pytest.fixture
def jaeger_url() -> str:
    """Provide Jaeger URL from environment."""
    return os.environ.get("JAEGER_URL", "http://localhost:16686")


@pytest.fixture
def http_client(backend_url: str) -> RealHTTPClient:
    """Provide a real HTTP client for backend testing."""
    client = RealHTTPClient(backend_url)
    yield client
    client.close()


@pytest.fixture
def prometheus_client(prometheus_url: str) -> RealHTTPClient:
    """Provide a real HTTP client for Prometheus testing."""
    client = RealHTTPClient(prometheus_url)
    yield client
    client.close()


@pytest.fixture
def grafana_client(grafana_url: str) -> RealHTTPClient:
    """Provide a real HTTP client for Grafana testing."""
    client = RealHTTPClient(grafana_url)
    yield client
    client.close()


@pytest.fixture
def service_endpoints() -> List[ServiceEndpoint]:
    """Provide configured service endpoints."""
    return get_service_endpoints()


@pytest.fixture
def deployment_status() -> DeploymentStatus:
    """Provide deployment status tracker."""
    return DeploymentStatus()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "smoke: mark test as a smoke test (requires running services)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires running services)",
    )
    config.addinivalue_line(
        "markers",
        "observability: mark test as observability stack test",
    )
