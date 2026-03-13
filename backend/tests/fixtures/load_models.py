"""
Load test models and profiles.

Provides test data for:
- Baseline performance (FR-024)
- Peak traffic handling (FR-025)
- Sustained load endurance (FR-026)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LoadTestCriteria:
    """Success criteria for load tests."""

    max_p95_latency_ms: float
    max_error_rate_percent: float
    max_memory_growth_percent: float
    max_cpu_percent: float


@dataclass
class LoadTestProfile:
    """Model for load test profiles (FR-024, FR-025, FR-026)."""

    name: str
    concurrent_users: int
    spawn_rate: float  # users per second
    duration_seconds: int
    target_endpoints: List[str]
    success_criteria: LoadTestCriteria
    description: str = ""

    def __repr__(self) -> str:
        return (
            f"LoadTestProfile(name={self.name}, "
            f"users={self.concurrent_users}, "
            f"duration={self.duration_seconds}s)"
        )


@dataclass
class LoadTestResult:
    """Model for load test results."""

    profile_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    failed_requests: int = 0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    requests_per_second: float = 0.0
    error_rate_percent: float = 0.0
    memory_growth_percent: float = 0.0
    cpu_percent: float = 0.0
    errors_by_type: dict = field(default_factory=dict)

    def meets_criteria(self, criteria: LoadTestCriteria) -> bool:
        """Check if results meet the specified criteria."""
        return (
            self.p95_latency_ms <= criteria.max_p95_latency_ms
            and self.error_rate_percent <= criteria.max_error_rate_percent
            and self.memory_growth_percent <= criteria.max_memory_growth_percent
            and self.cpu_percent <= criteria.max_cpu_percent
        )

    @property
    def success_rate_percent(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100

    def __repr__(self) -> str:
        return (
            f"LoadTestResult(profile={self.profile_name}, "
            f"requests={self.total_requests}, "
            f"p95={self.p95_latency_ms:.2f}ms, "
            f"error_rate={self.error_rate_percent:.2f}%)"
        )


# ==============================================================
# Predefined Load Test Profiles (per spec requirements)
# ==============================================================

LOAD_TEST_PROFILES = {
    "baseline": LoadTestProfile(
        name="baseline",
        concurrent_users=100,
        spawn_rate=10,
        duration_seconds=300,  # 5 minutes
        target_endpoints=[
            "/api/v1/inventario/products/",
            "/api/v1/inventario/stock/",
            "/api/v1/sync/sessions/",
        ],
        success_criteria=LoadTestCriteria(
            max_p95_latency_ms=500,  # FR-024
            max_error_rate_percent=1.0,
            max_memory_growth_percent=20,
            max_cpu_percent=80,
        ),
        description="Baseline performance with 100 concurrent users",
    ),
    "peak": LoadTestProfile(
        name="peak",
        concurrent_users=500,
        spawn_rate=50,
        duration_seconds=300,  # 5 minutes
        target_endpoints=[
            "/api/v1/inventario/products/",
            "/api/v1/inventario/stock/",
        ],
        success_criteria=LoadTestCriteria(
            max_p95_latency_ms=1000,  # More lenient at peak
            max_error_rate_percent=1.0,  # FR-025
            max_memory_growth_percent=30,
            max_cpu_percent=90,
        ),
        description="Peak traffic handling with 500 concurrent users",
    ),
    "sustained": LoadTestProfile(
        name="sustained",
        concurrent_users=100,
        spawn_rate=10,
        duration_seconds=600,  # FR-026: 10 minutes
        target_endpoints=[
            "/api/v1/inventario/products/",
            "/api/v1/inventario/stock/",
        ],
        success_criteria=LoadTestCriteria(
            max_p95_latency_ms=500,
            max_error_rate_percent=1.0,
            max_memory_growth_percent=10,  # Stability over time
            max_cpu_percent=70,
        ),
        description="Sustained load endurance for 10 minutes",
    ),
    "stress": LoadTestProfile(
        name="stress",
        concurrent_users=1000,
        spawn_rate=100,
        duration_seconds=120,  # 2 minutes
        target_endpoints=[
            "/api/v1/inventario/products/",
        ],
        success_criteria=LoadTestCriteria(
            max_p95_latency_ms=2000,
            max_error_rate_percent=5.0,  # More lenient
            max_memory_growth_percent=50,
            max_cpu_percent=95,
        ),
        description="Stress test to find system limits",
    ),
    "multi_tenant": LoadTestProfile(
        name="multi_tenant",
        concurrent_users=200,
        spawn_rate=20,
        duration_seconds=300,
        target_endpoints=[
            "/api/v1/inventario/products/",
            "/api/v1/inventario/stock/",
            "/api/v1/auth/token/",
        ],
        success_criteria=LoadTestCriteria(
            max_p95_latency_ms=500,
            max_error_rate_percent=1.0,
            max_memory_growth_percent=25,
            max_cpu_percent=85,
        ),
        description="Multi-tenant isolation under load",
    ),
}


@dataclass
class EndpointWeight:
    """Endpoint weight configuration for load testing."""

    endpoint: str
    method: str
    weight: int  # Relative frequency
    requires_auth: bool
    sample_payload: Optional[dict] = None


# Weighted endpoint distribution for realistic traffic simulation
ENDPOINT_WEIGHTS = [
    EndpointWeight(
        endpoint="/api/v1/inventario/products/",
        method="GET",
        weight=40,  # 40% of traffic
        requires_auth=True,
    ),
    EndpointWeight(
        endpoint="/api/v1/inventario/stock/",
        method="GET",
        weight=30,  # 30% of traffic
        requires_auth=True,
    ),
    EndpointWeight(
        endpoint="/api/v1/sync/sessions/",
        method="POST",
        weight=15,  # 15% of traffic
        requires_auth=True,
        sample_payload={"device_id": "POS-TERMINAL-001", "operation": "sync_products"},
    ),
    EndpointWeight(
        endpoint="/api/v1/auth/token/",
        method="POST",
        weight=10,  # 10% of traffic
        requires_auth=False,
        sample_payload={"email": "test@test.com", "password": "TestPassword123!"},
    ),
    EndpointWeight(
        endpoint="/api/health/live/",
        method="GET",
        weight=5,  # 5% of traffic (health checks)
        requires_auth=False,
    ),
]
