"""
Test fixtures module.

Provides reusable fixtures and data models for:
- Security testing (JWT attacks, rate limiting, encryption, tenant isolation)
- Docker integration testing (health checks, graceful shutdown, network)
- Property-based testing (Hypothesis strategies)
- Load testing (Locust profiles)
- API fuzzing (Schemathesis configuration)
- Test traceability (requirement mapping)
- Cache mocking (FR-003: consolidated mock_cache)
- Observability testing (FR-010: gauge metrics)
"""

from tests.fixtures.cache import (
    mock_cache,
    mock_cache_with_attempts,
    mock_cache_lockout_scenario,
    mock_cache_rate_window,
    mock_redis_cache,
    mock_cache_stateful,
)
from tests.fixtures.docker_models import (
    DOCKER_SERVICES_CONFIG,
    EXPECTED_NETWORK_TOPOLOGY,
    HEALTH_CHECK_ENDPOINTS,
    DatabaseConnectionTest,
    GracefulShutdownResult,
    HealthCheckResult,
    NetworkConnectivityTest,
)
from tests.fixtures.fuzz_models import (
    DEFAULT_SCHEMATHESIS_CONFIG,
    EDGE_CASE_PAYLOADS,
    EXPECTED_ERROR_FORMATS,
    FUZZ_TARGET_ENDPOINTS,
    FuzzingReport,
    FuzzingResult,
    SchemathesisConfig,
)
from tests.fixtures.load_models import (
    ENDPOINT_WEIGHTS,
    LOAD_TEST_PROFILES,
    LoadTestCriteria,
    LoadTestProfile,
    LoadTestResult,
)
from tests.fixtures.property_strategies import (
    barcode,
    boundary_prices,
    boundary_quantities,
    cost_price,
    discount_percentage,
    inventory_quantity,
    invalid_sku_patterns,
    price_calculation_scenario,
    product_data,
    product_name,
    sku_strategy,
    stock_movement_data,
    tax_rate,
    tenant_resource_data,
    unit_price,
    user_data,
    valid_stock_quantity,
)
from tests.fixtures.security import (
    CROSS_TENANT_TEST_CASES,
    ENCRYPTION_TEST_CASES,
    JWT_ATTACK_VECTORS,
    OWASP_INJECTION_PAYLOADS,
    RATE_LIMIT_TEST_CASES,
    CrossTenantAccessTest,
    EncryptionTestCase,
    JWTAttackVector,
    RateLimitTestCase,
)
from tests.fixtures.traceability_models import (
    REQUIREMENT_TEST_MAP,
    RequirementTestMapping,
    TraceabilityMatrix,
    build_traceability_matrix,
)
from tests.fixtures.observability import (
    isolated_registry,
    orders_gauge,
    stock_gauge,
    sessions_gauge,
    sync_operations_gauge,
    request_counter,
    request_latency_histogram,
    gauge_test_helper,
    multi_tenant_gauge_scenario,
)

__all__ = [
    # Cache (FR-003: consolidated mock_cache)
    "mock_cache",
    "mock_cache_with_attempts",
    "mock_cache_lockout_scenario",
    "mock_cache_rate_window",
    "mock_redis_cache",
    "mock_cache_stateful",
    # Security
    "JWTAttackVector",
    "JWT_ATTACK_VECTORS",
    "RateLimitTestCase",
    "RATE_LIMIT_TEST_CASES",
    "CrossTenantAccessTest",
    "CROSS_TENANT_TEST_CASES",
    "EncryptionTestCase",
    "ENCRYPTION_TEST_CASES",
    "OWASP_INJECTION_PAYLOADS",
    # Docker
    "HealthCheckResult",
    "GracefulShutdownResult",
    "NetworkConnectivityTest",
    "DatabaseConnectionTest",
    "EXPECTED_NETWORK_TOPOLOGY",
    "HEALTH_CHECK_ENDPOINTS",
    "DOCKER_SERVICES_CONFIG",
    # Property
    "inventory_quantity",
    "valid_stock_quantity",
    "unit_price",
    "cost_price",
    "tax_rate",
    "discount_percentage",
    "sku_strategy",
    "product_name",
    "barcode",
    "product_data",
    "stock_movement_data",
    "price_calculation_scenario",
    "tenant_resource_data",
    "user_data",
    "boundary_prices",
    "boundary_quantities",
    "invalid_sku_patterns",
    # Load
    "LoadTestProfile",
    "LoadTestCriteria",
    "LoadTestResult",
    "LOAD_TEST_PROFILES",
    "ENDPOINT_WEIGHTS",
    # Fuzz
    "FuzzingResult",
    "FuzzingReport",
    "SchemathesisConfig",
    "DEFAULT_SCHEMATHESIS_CONFIG",
    "FUZZ_TARGET_ENDPOINTS",
    "EDGE_CASE_PAYLOADS",
    "EXPECTED_ERROR_FORMATS",
    # Traceability
    "RequirementTestMapping",
    "TraceabilityMatrix",
    "REQUIREMENT_TEST_MAP",
    "build_traceability_matrix",
    # Observability (FR-010: gauge metrics)
    "isolated_registry",
    "orders_gauge",
    "stock_gauge",
    "sessions_gauge",
    "sync_operations_gauge",
    "request_counter",
    "request_latency_histogram",
    "gauge_test_helper",
    "multi_tenant_gauge_scenario",
]
