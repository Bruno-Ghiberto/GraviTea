"""
Docker integration test models and fixtures.

Provides test data for:
- Health check validation (FR-013, FR-014)
- Graceful shutdown (FR-015)
- Network topology (FR-016)
- Database connections (FR-017)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class HealthCheckResult:
    """Model for health check test results (FR-013, FR-014)."""

    service_name: str
    endpoint: str
    response_time_ms: float
    status_code: Optional[int]
    is_healthy: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict] = None
    response_body: Optional[Dict] = None
    error: Optional[str] = None

    def meets_sla(self) -> bool:
        """FR-014: Health checks MUST respond within 5 seconds."""
        return self.response_time_ms < 5000 and self.is_healthy

    @property
    def is_connection_error(self) -> bool:
        """Check if the result represents a connection error."""
        return self.status_code is None and self.error is not None

    @property
    def is_reachable(self) -> bool:
        """Check if the service was reachable (regardless of health status)."""
        return self.status_code is not None

    def require_reachable(self, message: str = "") -> "HealthCheckResult":
        """
        Assert that the service is reachable. Raises AssertionError if not.

        Use this for strict validation that fails tests when services are down.
        """
        if not self.is_reachable:
            raise AssertionError(
                f"Service not reachable at {self.endpoint}. "
                f"Error: {self.error}. "
                f"{message}"
            )
        return self

    def require_healthy(self, message: str = "") -> "HealthCheckResult":
        """
        Assert that the service is healthy. Raises AssertionError if not.

        Use this for strict validation in deployment readiness tests.
        """
        self.require_reachable(message)
        if not self.is_healthy:
            raise AssertionError(
                f"Service at {self.endpoint} is not healthy. "
                f"Status: {self.status_code}. "
                f"{message}"
            )
        return self

    def __repr__(self) -> str:
        return (
            f"HealthCheckResult(service={self.service_name}, "
            f"status={self.status_code}, "
            f"time_ms={self.response_time_ms:.2f}, "
            f"healthy={self.is_healthy})"
        )


@dataclass
class GracefulShutdownResult:
    """Model for graceful shutdown test results (FR-015)."""

    service_name: str
    signal_sent: str  # 'SIGTERM'
    shutdown_time_ms: float
    in_flight_requests_completed: int
    connections_drained: bool
    exit_code: int
    error_message: Optional[str] = None

    def meets_sla(self) -> bool:
        """FR-015: Services MUST support graceful shutdown with 30-second drain."""
        return self.shutdown_time_ms < 30000 and self.connections_drained and self.exit_code == 0

    def __repr__(self) -> str:
        return (
            f"GracefulShutdownResult(service={self.service_name}, "
            f"signal={self.signal_sent}, "
            f"time_ms={self.shutdown_time_ms:.2f}, "
            f"drained={self.connections_drained})"
        )


@dataclass
class NetworkConnectivityTest:
    """Model for network topology tests (FR-016)."""

    source_service: str
    target_service: str
    network_name: str
    connection_successful: bool
    latency_ms: float
    error_message: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"NetworkConnectivityTest({self.source_service} -> {self.target_service} "
            f"on {self.network_name}: {'OK' if self.connection_successful else 'FAILED'})"
        )


# Expected network topology per docker-compose.yml
EXPECTED_NETWORK_TOPOLOGY: Dict[str, List[str]] = {
    "test-default": ["postgres-test", "redis-test", "web-test"],
    "test-shared": ["web-test", "jaeger-test", "prometheus-test"],
}


@dataclass
class DatabaseConnectionTest:
    """Model for database connection tests (FR-017)."""

    conn_max_age: int
    pool_size: int
    connections_created: int
    connections_reused: int
    leak_detected: bool
    max_concurrent_connections: int
    connection_timeout_ms: float

    def is_cloud_run_compatible(self) -> bool:
        """FR-017: Database connections MUST use CONN_MAX_AGE=0."""
        return self.conn_max_age == 0 and not self.leak_detected

    def __repr__(self) -> str:
        return (
            f"DatabaseConnectionTest(conn_max_age={self.conn_max_age}, "
            f"pool_size={self.pool_size}, "
            f"leak_detected={self.leak_detected}, "
            f"cloud_run_compatible={self.is_cloud_run_compatible()})"
        )


# Health check endpoints configuration
# Note: Django routes are defined WITHOUT trailing slashes in apps/core/health/urls.py
HEALTH_CHECK_ENDPOINTS = [
    {
        "name": "liveness",
        "endpoint": "/health/live",
        "url": "http://localhost:8001/health/live",
        "expected_status": 200,
        "timeout_ms": 5000,
        "max_response_time_ms": 5000,
        "description": "Kubernetes liveness probe endpoint",
    },
    {
        "name": "readiness",
        "endpoint": "/health/ready",
        "url": "http://localhost:8001/health/ready",
        "expected_status": 200,
        "timeout_ms": 5000,
        "max_response_time_ms": 5000,
        "description": "Kubernetes readiness probe endpoint",
    },
    {
        "name": "startup",
        "endpoint": "/health/startup",
        "url": "http://localhost:8001/health/startup",
        "expected_status": 200,
        "timeout_ms": 5000,
        "max_response_time_ms": 5000,
        "description": "Kubernetes startup probe endpoint",
    },
]


# Docker services configuration for testing
DOCKER_SERVICES_CONFIG = {
    "postgres-test": {
        "image": "postgres:18-alpine",
        "port": 5433,
        "healthcheck_cmd": "pg_isready -U gravitea_test -d gravitea_test",
        "startup_timeout_s": 30,
    },
    "redis-test": {
        "image": "redis:7-alpine",
        "port": 6380,
        "healthcheck_cmd": "redis-cli ping",
        "startup_timeout_s": 10,
    },
    "web-test": {
        "image": "gravitea-web-test",
        "port": 8001,
        "healthcheck_endpoint": "/health/live",
        "startup_timeout_s": 60,
        "graceful_shutdown_timeout_s": 30,
    },
    "jaeger-test": {
        "image": "jaegertracing/all-in-one:1.50",
        "port": 16687,
        "healthcheck_endpoint": "/",
        "startup_timeout_s": 30,
    },
    "prometheus-test": {
        "image": "prom/prometheus:v2.47.0",
        "port": 9091,
        "healthcheck_endpoint": "/-/ready",
        "startup_timeout_s": 30,
    },
}
