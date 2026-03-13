"""
Test constants module for GRAVITEA backend tests.

FR-012: Extract hardcoded test values to constants module.

This module centralizes all test constants to ensure consistency across
the test suite and eliminate magic values scattered throughout test files.
"""

# =============================================================================
# JWT Test Constants
# =============================================================================

JWT_TEST_SECRET = "test-secret-key-for-jwt-testing-only-do-not-use-in-production"
JWT_TEST_ALGORITHM = "HS256"
JWT_TEST_ALGORITHM_RS256 = "RS256"
JWT_TEST_EXPIRY_MINUTES = 15
JWT_TEST_REFRESH_DAYS = 7

# Invalid/attack algorithms for security testing
JWT_INVALID_ALGORITHMS = ["none", "None", "NONE", "nOnE"]


# =============================================================================
# Rate Limit Constants
# =============================================================================

# Lockout thresholds (number of failed attempts)
RATE_LIMIT_LOCKOUT_5 = 5    # 5 failures -> 5 min lockout
RATE_LIMIT_LOCKOUT_30 = 10  # 10 failures -> 30 min lockout
RATE_LIMIT_PERMANENT = 20   # 20 failures -> permanent lock

# Lockout durations in seconds
RATE_LIMIT_DURATION_5_MIN = 300      # 5 minutes
RATE_LIMIT_DURATION_30_MIN = 1800    # 30 minutes

# Rate limit windows
RATE_LIMIT_WINDOW_SECONDS = 60


# =============================================================================
# SSRF Test Constants (OWASP A10:2021)
# =============================================================================

SSRF_INTERNAL_HOSTS = [
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "127.0.0.2",
    "127.1",
    "[::1]",
]

SSRF_METADATA_HOSTS = [
    "169.254.169.254",                    # AWS metadata
    "metadata.google.internal",           # GCP metadata
    "169.254.170.2",                      # AWS ECS task metadata
    "fd00:ec2::254",                      # AWS IPv6 metadata
]

SSRF_PRIVATE_NETWORKS = [
    "10.0.0.1",
    "172.16.0.1",
    "192.168.1.1",
]

SSRF_DANGEROUS_SCHEMES = [
    "file:///etc/passwd",
    "file:///etc/shadow",
    "gopher://localhost:25/",
    "dict://localhost:11211/",
]


# =============================================================================
# Test Tenant Constants
# =============================================================================

TEST_TENANT_NAME = "Test Tenant"
TEST_TENANT_SLUG = "test-tenant"
TEST_TENANT_DOMAIN = "test.gravitea.local"

OTHER_TENANT_NAME = "Other Tenant"
OTHER_TENANT_SLUG = "other-tenant"
OTHER_TENANT_DOMAIN = "other.gravitea.local"

ATTACKER_TENANT_NAME = "Attacker Tenant"
ATTACKER_TENANT_SLUG = "attacker-tenant"


# =============================================================================
# Test User Constants
# =============================================================================

TEST_USER_PASSWORD = "TestPassword123!"
TEST_USER_EMAIL_TEMPLATE = "test-{role}@{tenant}.gravitea.local"

TEST_ADMIN_EMAIL = "admin@test.gravitea.local"
TEST_SALES_EMAIL = "sales@test.gravitea.local"
TEST_VIEWER_EMAIL = "viewer@test.gravitea.local"


# =============================================================================
# Timeout Constants (in seconds)
# =============================================================================

TEST_TIMEOUT_FAST = 5       # Fast unit tests
TEST_TIMEOUT_NORMAL = 30    # Normal tests
TEST_TIMEOUT_SLOW = 300     # Slow/integration tests
TEST_TIMEOUT_DOCKER = 600   # Docker-based tests


# =============================================================================
# Mass Assignment Test Constants
# =============================================================================

# Fields that should never be settable via API
FORBIDDEN_FIELDS_TENANT = ["tenant_id", "tenant"]
FORBIDDEN_FIELDS_USER = ["is_admin", "is_superuser", "is_staff"]
FORBIDDEN_FIELDS_AUDIT = ["created_at", "updated_at", "created_by", "modified_by"]

# Endpoints for mass assignment testing
MASS_ASSIGNMENT_ENDPOINTS = [
    "/api/v1/products/",
    "/api/v1/categories/",
    "/api/v1/compras/suppliers/",
    "/api/v1/price-lists/",
    "/api/v1/inventory/movements/",
    "/api/v1/roles/",
    "/api/v1/users/",
    "/api/v1/sync/sessions/",
    "/api/v1/sync/operations/",
]


# =============================================================================
# XSS Test Payloads
# =============================================================================

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<body onload=alert(1)>",
    "javascript:alert(1)",
    "<iframe src='javascript:alert(1)'>",
    "'\"><script>alert(1)</script>",
    "<div onmouseover='alert(1)'>hover</div>",
]


# =============================================================================
# SQL Injection Test Payloads
# =============================================================================

SQL_INJECTION_PAYLOADS = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "1; SELECT * FROM users--",
    "admin'--",
    "1 UNION SELECT * FROM users",
]


# =============================================================================
# Observability Test Constants
# =============================================================================

# Metric names for gauge tests
METRIC_ORDERS_IN_PROGRESS = "gravitea_orders_in_progress"
METRIC_LOW_STOCK_ALERTS = "gravitea_low_stock_alerts"
METRIC_ACTIVE_SESSIONS = "gravitea_active_sessions"

# Default label values for testing
DEFAULT_TENANT_LABEL = "test-tenant"
DEFAULT_PRODUCT_LABEL = "test-product"


# =============================================================================
# Test Data Limits
# =============================================================================

MAX_PRODUCTS_PER_TENANT = 1000
MAX_STOCK_MOVEMENTS = 10000
MAX_CONCURRENT_SESSIONS = 100
MAX_SYNC_OPERATIONS = 5000
