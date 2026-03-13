"""
Locust Load Test Definitions.

Provides Locust user behavior classes for load testing the GRAVITEA ERP API.
Used by FR-024, FR-025, FR-026 compliance tests.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8001
"""

import json
import os
import random
import time
from typing import Dict, Optional, List
from uuid import uuid4

from locust import HttpUser, task, between, events
from locust.env import Environment

from tests.fixtures.load_models import (
    ENDPOINT_WEIGHTS,
    EndpointWeight,
)


class GraviteaUser(HttpUser):
    """
    Base user class for GRAVITEA ERP load testing.

    Simulates realistic user behavior with proper authentication
    and multi-tenant context.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    # Default headers for authenticated requests
    default_headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None
        self.tenant_id: str = str(uuid4())
        self.branch_id: str = str(uuid4())
        self.user_email: str = f"loadtest_{uuid4().hex[:8]}@test.gravitea.com"

    def on_start(self):
        """Called when a simulated user starts. Performs authentication."""
        self._authenticate()

    def _authenticate(self):
        """Authenticate and obtain JWT token."""
        # In a real test, this would authenticate against the actual API
        # For now, simulate token generation
        credentials = {
            "email": self.user_email,
            "password": "LoadTest123!",
        }

        # Try to authenticate (may fail in test environment)
        try:
            response = self.client.post(
                "/api/v1/auth/token/",
                json=credentials,
                headers={"Content-Type": "application/json"},
                name="/api/v1/auth/token/ [auth]",
            )
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access")
            else:
                # Use mock token for testing
                self.auth_token = f"mock_token_{uuid4().hex}"
        except Exception:
            self.auth_token = f"mock_token_{uuid4().hex}"

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        headers = self.default_headers.copy()
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        headers["X-Tenant-ID"] = self.tenant_id
        return headers

    @task(40)
    def get_products(self):
        """GET /api/v1/inventario/products/ - 40% of traffic."""
        self.client.get(
            "/api/v1/inventario/products/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/products/ [list]",
        )

    @task(30)
    def get_stock(self):
        """GET /api/v1/inventario/stock/ - 30% of traffic."""
        self.client.get(
            "/api/v1/inventario/stock/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/stock/ [list]",
        )

    @task(15)
    def create_sync_session(self):
        """POST /api/v1/sync/sessions/ - 15% of traffic."""
        payload = {
            "device_id": f"POS-{uuid4().hex[:8].upper()}",
            "operation": "sync_products",
        }
        self.client.post(
            "/api/v1/sync/sessions/",
            json=payload,
            headers=self._get_auth_headers(),
            name="/api/v1/sync/sessions/ [create]",
        )

    @task(10)
    def refresh_token(self):
        """POST /api/v1/auth/token/ - 10% of traffic (token refresh)."""
        self._authenticate()

    @task(5)
    def health_check(self):
        """GET /health/live/ - 5% of traffic."""
        self.client.get(
            "/health/live/",
            name="/health/live/ [health]",
        )


class MultiTenantUser(GraviteaUser):
    """
    User class that simulates multiple tenants accessing the system.

    Each user is assigned to a different tenant to test tenant isolation
    under load.
    """

    # Class-level tenant pool
    tenant_pool: List[str] = [str(uuid4()) for _ in range(20)]
    user_count: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assign tenant round-robin
        MultiTenantUser.user_count += 1
        tenant_index = MultiTenantUser.user_count % len(self.tenant_pool)
        self.tenant_id = self.tenant_pool[tenant_index]

    @task(20)
    def get_tenant_products(self):
        """
        Get products for specific tenant.

        Tests that tenant isolation is maintained under load.
        """
        self.client.get(
            "/api/v1/inventario/products/",
            headers=self._get_auth_headers(),
            name=f"/api/v1/inventario/products/ [tenant]",
        )


class ReadHeavyUser(GraviteaUser):
    """
    User class that simulates read-heavy workload.

    Typical for POS systems where reads far exceed writes.
    """

    @task(60)
    def get_products(self):
        """Heavy product listing - 60%."""
        self.client.get(
            "/api/v1/inventario/products/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/products/ [read]",
        )

    @task(35)
    def get_stock(self):
        """Heavy stock checking - 35%."""
        self.client.get(
            "/api/v1/inventario/stock/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/stock/ [read]",
        )

    @task(5)
    def health_check(self):
        """Health check - 5%."""
        self.client.get(
            "/health/live/",
            name="/health/live/ [health]",
        )


class WriteHeavyUser(GraviteaUser):
    """
    User class that simulates write-heavy workload.

    Tests database write performance and locking behavior.
    """

    @task(40)
    def create_product(self):
        """Create new products - 40%."""
        payload = {
            "sku": f"SKU-{uuid4().hex[:8].upper()}",
            "name": f"Test Product {random.randint(1, 10000)}",
            "unit_price": str(random.uniform(10.00, 1000.00)),
            "cost_price": str(random.uniform(5.00, 500.00)),
            "tax_rate": "21.00",
            "is_active": True,
        }
        self.client.post(
            "/api/v1/inventario/products/",
            json=payload,
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/products/ [create]",
        )

    @task(40)
    def update_stock(self):
        """Update stock levels - 40%."""
        payload = {
            "quantity_delta": str(random.uniform(-10, 100)),
            "movement_type": random.choice(["PURCHASE", "SALE", "ADJUSTMENT"]),
            "notes": f"Load test movement {uuid4().hex[:8]}",
        }
        # Simulate stock update (may fail without real product ID)
        self.client.post(
            "/api/v1/inventario/stock/movements/",
            json=payload,
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/stock/movements/ [create]",
        )

    @task(20)
    def create_sync_session(self):
        """Sync operations - 20%."""
        payload = {
            "device_id": f"POS-{uuid4().hex[:8].upper()}",
            "operation": "sync_all",
        }
        self.client.post(
            "/api/v1/sync/sessions/",
            json=payload,
            headers=self._get_auth_headers(),
            name="/api/v1/sync/sessions/ [write]",
        )


class StressTestUser(GraviteaUser):
    """
    User class for stress testing.

    Aggressive request patterns to find system limits.
    """

    wait_time = between(0.1, 0.5)  # Very fast requests

    @task(50)
    def rapid_product_reads(self):
        """Rapid product reads to stress read path."""
        self.client.get(
            "/api/v1/inventario/products/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/products/ [stress]",
        )

    @task(30)
    def rapid_stock_reads(self):
        """Rapid stock reads."""
        self.client.get(
            "/api/v1/inventario/stock/",
            headers=self._get_auth_headers(),
            name="/api/v1/inventario/stock/ [stress]",
        )

    @task(20)
    def rapid_writes(self):
        """Rapid write operations."""
        payload = {
            "device_id": f"STRESS-{uuid4().hex[:4]}",
            "operation": "stress_test",
        }
        self.client.post(
            "/api/v1/sync/sessions/",
            json=payload,
            headers=self._get_auth_headers(),
            name="/api/v1/sync/sessions/ [stress]",
        )


# Event hooks for custom metrics collection
@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response,
    context,
    exception,
    **kwargs
):
    """Hook to capture additional metrics per request."""
    # Can be extended to push metrics to Prometheus, etc.
    pass


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    """Called when a load test starts."""
    print(f"Load test starting with {environment.runner.user_count} users")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs):
    """Called when a load test stops."""
    stats = environment.stats
    print(f"\n=== Load Test Summary ===")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    if stats.total.num_requests > 0:
        print(f"Requests/sec: {stats.total.total_rps:.2f}")
