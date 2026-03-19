"""
Pytest configuration and fixtures for Gravitea ERP tests.

Provides fixtures for tenant isolation, authentication, and test data.
"""

# ============================================================
# Python 3.14.3+ Django Compatibility Patch
# ============================================================
# Django 5.0.14 has a bug in Context.__copy__ that fails with Python 3.14
# when copying template contexts. The bug is in django/template/context.py:39
# where `copy(super())` doesn't preserve the `dicts` attribute correctly.
#
# This monkey patch fixes the issue by providing a correct implementation
# of __copy__ that works with Python 3.14's copy semantics.
#
# Error: AttributeError: 'super' object has no attribute 'dicts'
# Affects: Tests that trigger 404 errors or template rendering
# ============================================================
import sys

if sys.version_info >= (3, 14):
    import copy as _copy_module

    def _patched_base_context_copy(self):
        """Fixed __copy__ for Django's BaseContext that works with Python 3.14."""
        # Create a new instance of the same class
        duplicate = self.__class__()
        # Copy the dicts list (shallow copy of the list)
        duplicate.dicts = self.dicts[:]
        return duplicate

    def _patched_context_copy(self):
        """Fixed __copy__ for Django's Context that works with Python 3.14."""
        from django.template.context import BaseContext
        # Use BaseContext.__copy__ logic but preserve Context-specific attributes
        duplicate = self.__class__(self)
        # Copy the dicts from BaseContext
        duplicate.dicts = self.dicts[:]
        # Copy Context-specific attributes
        if hasattr(self, 'render_context'):
            duplicate.render_context = self.render_context
        if hasattr(self, 'autoescape'):
            duplicate.autoescape = self.autoescape
        if hasattr(self, 'use_l10n'):
            duplicate.use_l10n = self.use_l10n
        if hasattr(self, 'use_tz'):
            duplicate.use_tz = self.use_tz
        return duplicate

    def _apply_django_context_patch():
        """Apply the Context copy patch if Django is available."""
        try:
            from django.template.context import BaseContext, Context
            BaseContext.__copy__ = _patched_base_context_copy
            Context.__copy__ = _patched_context_copy
        except ImportError:
            # Django not installed yet, will be patched when loaded
            pass

    # Apply patch immediately
    _apply_django_context_patch()


import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.models import Role
from apps.core.managers.tenant_bound import (clear_current_tenant_id,
                                             get_current_tenant_id,
                                             set_current_tenant_id)
from apps.core.models import Branch, Tenant

# FR-003: Import consolidated cache fixtures
from tests.fixtures.cache import (
    mock_cache,
    mock_cache_with_attempts,
    mock_cache_lockout_scenario,
    mock_cache_rate_window,
    mock_redis_cache,
    mock_cache_stateful,
)

# FR-010: Import observability fixtures
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


# ============================================================
# Hypothesis Configuration
# ============================================================
# Note: hypothesis_profile in pytest.ini is not a valid option.
# Configure Hypothesis profiles here instead.
try:
    from hypothesis import settings, Verbosity

    # Register test profiles for different environments
    settings.register_profile("ci", max_examples=100)
    settings.register_profile("dev", max_examples=10)
    settings.register_profile(
        "debug",
        max_examples=10,
        verbosity=Verbosity.verbose,
    )
    # Load default profile (can be overridden via HYPOTHESIS_PROFILE env var)
    settings.load_profile("dev")
except ImportError:
    # Hypothesis not installed, skip configuration
    pass


User = get_user_model()


# ============================================================
# Tenant Fixtures
# ============================================================


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Company",
        plan_type="FREE",  # Valid choices: FREE, PRO, ENTERPRISE
        is_active=True,
    )


@pytest.fixture
def tenant_context(tenant):
    """Set up tenant context for tests."""
    set_current_tenant_id(tenant.id)
    yield tenant
    clear_current_tenant_id()


@pytest.fixture
def other_tenant(db):
    """Create a secondary tenant for isolation tests."""
    return Tenant.objects.create(
        name="Other Company",
        plan_type="FREE",  # Valid choices: FREE, PRO, ENTERPRISE
        is_active=True,
    )


# ============================================================
# Branch Fixtures
# ============================================================


@pytest.fixture
def branch(tenant_context):
    """Create a test branch."""
    return Branch.objects.create(
        tenant=tenant_context,
        name="Main Store",
        address="123 Test Street",
        is_active=True,
    )


@pytest.fixture
def other_branch(tenant_context):
    """Create a secondary branch."""
    return Branch.objects.create(
        tenant=tenant_context,
        name="Secondary Store",
        address="456 Other Avenue",
        is_active=True,
    )


# ============================================================
# Role Fixtures
# ============================================================


@pytest.fixture
def admin_role(tenant_context):
    """Create an admin role with all permissions."""
    return Role.objects.create(
        tenant=tenant_context,
        name="Administrator",
        permissions=[
            "inventory.read",
            "inventory.write",
            "inventory.create",
            "inventory.delete",
            "inventory.admin",
            "sales.read",
            "sales.write",
            "sales.create",
            "sales.delete",
            "sales.admin",
            "purchases.read",
            "purchases.write",
            "purchases.create",
            "purchases.delete",
            "purchases.admin",
            "customers.read",
            "customers.write",
            "customers.create",
            "customers.delete",
            "customers.admin",
            "reports.read",
            "reports.write",
            "reports.create",
            "reports.delete",
            "reports.admin",
            "reports.export",
            "settings.read",
            "settings.write",
            "settings.create",
            "settings.delete",
            "settings.admin",
        ],
    )


@pytest.fixture
def sales_role(tenant_context):
    """Create a sales role with limited permissions."""
    return Role.objects.create(
        tenant=tenant_context,
        name="Sales",
        permissions=[
            "inventory.read",
            "sales.read",
            "sales.write",
            "sales.create",
            "customers.read",
            "customers.write",
            "customers.create",
        ],
    )


@pytest.fixture
def viewer_role(tenant_context):
    """Create a viewer role with read-only permissions."""
    return Role.objects.create(
        tenant=tenant_context,
        name="Viewer",
        permissions=[
            "inventory.read",
            "sales.read",
            "customers.read",
            "reports.read",
        ],
    )


# ============================================================
# User Fixtures
# ============================================================


@pytest.fixture
def admin_user(tenant_context, admin_role, branch):
    """Create an admin user."""
    user = User.objects.create_user(
        email="admin@testcompany.com",
        tenant=tenant_context,
        password="TestPassword123!",
        full_name="Admin User",
        role=admin_role,
        default_branch=branch,
    )
    return user


@pytest.fixture
def sales_user(tenant_context, sales_role, branch):
    """Create a sales user."""
    user = User.objects.create_user(
        email="sales@testcompany.com",
        tenant=tenant_context,
        password="TestPassword123!",
        full_name="Sales User",
        role=sales_role,
        default_branch=branch,
    )
    return user


@pytest.fixture
def viewer_user(tenant_context, viewer_role, branch):
    """Create a viewer user."""
    user = User.objects.create_user(
        email="viewer@testcompany.com",
        tenant=tenant_context,
        password="TestPassword123!",
        full_name="Viewer User",
        role=viewer_role,
        default_branch=branch,
    )
    return user


@pytest.fixture
def other_tenant_user(other_tenant):
    """Create a user in a different tenant for isolation tests.

    Includes a full-permission role so cross-tenant tests verify IDOR/tenant
    isolation rather than being blocked by HasModulePermission.
    """
    # Save previous tenant context so we can restore it after creating other-tenant objects
    previous_tenant_id = get_current_tenant_id()
    set_current_tenant_id(other_tenant.id)
    try:
        branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Store",
            address="789 Other Street",
            is_active=True,
        )
        role = Role.objects.create(
            tenant=other_tenant,
            name="Other Admin",
            permissions=[
                "inventory.read", "inventory.write", "inventory.admin",
                "sales.read", "sales.write", "sales.create", "sales.admin",
                "purchases.read", "purchases.write", "purchases.create", "purchases.admin",
                "customers.read", "customers.write", "customers.create", "customers.admin",
                "reports.read", "reports.write", "reports.create", "reports.admin", "reports.export",
                "settings.read", "settings.write", "settings.admin",
            ],
        )
        user = User.objects.create_user(
            email="user@othercompany.com",
            tenant=other_tenant,
            password="TestPassword123!",
            full_name="Other User",
            role=role,
            default_branch=branch,
        )
        return user
    finally:
        if previous_tenant_id:
            set_current_tenant_id(previous_tenant_id)
        else:
            clear_current_tenant_id()


# ============================================================
# API Client Fixtures
# ============================================================


@pytest.fixture
def api_client():
    """Create an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, admin_user, tenant_context):
    """Create an authenticated API client with admin user using custom JWT."""
    from apps.auth.jwt import CustomTokenObtainPairSerializer

    # Use custom serializer to include tenant_id in token claims
    refresh = CustomTokenObtainPairSerializer.get_token(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def sales_client(api_client, sales_user, tenant_context):
    """Create an authenticated API client with sales user using custom JWT."""
    from apps.auth.jwt import CustomTokenObtainPairSerializer

    refresh = CustomTokenObtainPairSerializer.get_token(sales_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def viewer_client(api_client, viewer_user, tenant_context):
    """Create an authenticated API client with viewer user using custom JWT."""
    from apps.auth.jwt import CustomTokenObtainPairSerializer

    refresh = CustomTokenObtainPairSerializer.get_token(viewer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def other_tenant_client(other_tenant_user):
    """Create an authenticated client for a different tenant.

    Uses its own APIClient instance to avoid credential conflicts when
    a test uses both authenticated_client and other_tenant_client.
    """
    from apps.auth.jwt import CustomTokenObtainPairSerializer

    client = APIClient()
    refresh = CustomTokenObtainPairSerializer.get_token(other_tenant_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================
# Category Fixtures
# ============================================================


@pytest.fixture
def product_category(tenant_context):
    """Create a test product category."""
    from apps.inventario.models import ProductCategory

    return ProductCategory.objects.create(
        tenant=tenant_context,
        name="Test Category",
    )


@pytest.fixture
def child_category(tenant_context, product_category):
    """Create a child category for hierarchy tests."""
    from apps.inventario.models import ProductCategory

    return ProductCategory.objects.create(
        tenant=tenant_context,
        name="Child Category",
        parent=product_category,
    )


# ============================================================
# Product Fixtures
# ============================================================


@pytest.fixture
def product(tenant_context, product_category):
    """Create a test product."""
    from apps.inventario.models import Product

    return Product.objects.create(
        tenant=tenant_context,
        sku="TEST-001",
        name="Test Product",
        description="A test product for testing",
        category=product_category,
        unit_price=Decimal("100.000"),
        cost_price=Decimal("50.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )


@pytest.fixture
def product_with_barcode(tenant_context, product_category):
    """Create a test product with barcode."""
    from apps.inventario.models import Product

    return Product.objects.create(
        tenant=tenant_context,
        sku="TEST-002",
        barcode="1234567890123",
        name="Barcode Product",
        description="A product with barcode",
        category=product_category,
        unit_price=Decimal("200.000"),
        cost_price=Decimal("100.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )


@pytest.fixture
def inactive_product(tenant_context, product_category):
    """Create an inactive product."""
    from apps.inventario.models import Product

    return Product.objects.create(
        tenant=tenant_context,
        sku="TEST-INACTIVE",
        name="Inactive Product",
        category=product_category,
        unit_price=Decimal("50.000"),
        cost_price=Decimal("25.000"),
        is_active=False,
    )


# ============================================================
# Cross-Tenant Product Fixture
# ============================================================


@pytest.fixture
def other_tenant_product(other_tenant):
    """Create a product in a different tenant for isolation tests.

    Used for T055: Cross-tenant isolation test (returns 404).
    """
    from apps.inventario.models import Product, ProductCategory

    # Set tenant context for other_tenant to create objects
    set_current_tenant_id(other_tenant.id)
    try:
        category = ProductCategory.objects.create(
            tenant=other_tenant,
            name="Other Tenant Category",
        )
        product = Product.objects.create(
            tenant=other_tenant,
            sku="OTHER-TENANT-001",
            name="Other Tenant Product",
            description="Product belonging to a different tenant",
            category=category,
            unit_price=Decimal("150.000"),
            cost_price=Decimal("75.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        )
        return product
    finally:
        clear_current_tenant_id()


# ============================================================
# Stock Fixtures
# ============================================================


@pytest.fixture
def stock_movement(tenant_context, product, branch):
    """Create a stock movement."""
    from apps.inventario.models import StockMovement

    return StockMovement.objects.create(
        tenant=tenant_context,
        product=product,
        branch=branch,
        type=StockMovement.MovementType.PURCHASE,  # Field is 'type' not 'movement_type'
        quantity_delta=Decimal("100.0000"),  # Field is 'quantity_delta' not 'quantity'
        cost_snapshot=product.cost_price,  # Field is 'cost_snapshot' not 'unit_cost'
        reference_id=uuid.uuid4(),  # reference_id is a UUIDField
        notes="Initial stock purchase",
        # Note: StockMovement has no 'created_by' field
    )


@pytest.fixture
def branch_stock(product, branch, stock_movement):
    """Get or create stock snapshot (created by stock_movement fixture)."""
    from apps.inventario.models import StockSnapshot

    # StockSnapshot has no tenant field directly - it uses branch.tenant
    stock, _ = StockSnapshot.objects.get_or_create(
        product=product, branch=branch, defaults={"quantity": Decimal("100.0000")}
    )
    return stock


# ============================================================
# Sync Fixtures
# ============================================================


@pytest.fixture
def sync_session(tenant_context, branch):
    """Create a sync session for a POS terminal."""
    from apps.sync.models import SyncSession

    return SyncSession.objects.create(
        tenant=tenant_context,
        branch=branch,
        device_id="POS-TERMINAL-001",
        status=SyncSession.SyncStatus.PENDING,
    )


# ============================================================
# Factory Fixtures
# ============================================================


@pytest.fixture
def product_factory(tenant_context, product_category):
    """Factory for creating products."""
    from apps.inventario.models import Product

    def create_product(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "sku": f"PROD-{uuid.uuid4().hex[:8].upper()}",
            "name": f"Product {uuid.uuid4().hex[:6]}",
            "category": product_category,
            "unit_price": Decimal("100.000"),
            "cost_price": Decimal("50.000"),
            "tax_rate": Decimal("21.00"),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    return create_product


@pytest.fixture
def user_factory(tenant_context, branch):
    """Factory for creating users."""

    def create_user(**kwargs):
        defaults = {
            "email": f"user-{uuid.uuid4().hex[:8]}@test.com",
            "tenant": tenant_context,
            "password": "TestPassword123!",
            "full_name": f"Test User {uuid.uuid4().hex[:6]}",
            "default_branch": branch,
        }
        defaults.update(kwargs)
        password = defaults.pop("password")
        user = User(**defaults)
        user.set_password(password)
        user.save()
        return user

    return create_user


# ============================================================
# Cleanup Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def cleanup_tenant_context():
    """Automatically clean up tenant context after each test."""
    yield
    clear_current_tenant_id()


@pytest.fixture(autouse=True)
def set_rls_tenant_context(request, tenant_context):
    """Set PostgreSQL session variable for RLS policy enforcement.

    Per R9: Application-level set_current_tenant_id() (in tenant_context fixture)
    only sets a Python thread-local. This fixture adds the DB-level session
    variable needed for RLS policies (SET app.current_tenant_id).

    Skips for @pytest.mark.unit tests (no DB connection).
    """
    if "unit" in [m.name for m in request.node.iter_markers()]:
        yield
        return

    from django.db import connection

    if connection.vendor != "postgresql":
        yield
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "SET app.current_tenant_id = %s",
            [str(tenant_context.id)],
        )
    yield
    with connection.cursor() as cursor:
        cursor.execute("RESET app.current_tenant_id")


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    """
    Clear the rate limit cache before and after each test.

    Ensures test isolation for rate limiting tests by preventing
    cache state from leaking between tests. Uses LocMemCache
    (configured in test.py) which actually stores data.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# ============================================================
# Encryption Test Fixtures
# ============================================================


@pytest.fixture
def test_encryption_key():
    """Generate a valid 32-byte encryption key for testing."""
    import base64
    import os

    return base64.b64encode(os.urandom(32)).decode("utf-8")


@pytest.fixture
def test_hmac_key():
    """Generate a valid 32-byte HMAC key for testing."""
    import base64
    import os

    return base64.b64encode(os.urandom(32)).decode("utf-8")


@pytest.fixture
def encryption_settings(test_encryption_key, test_hmac_key, settings):
    """Configure Django settings with test keys."""
    from apps.core.encryption.utils import get_encryption_key, get_hmac_key

    settings.ENCRYPTION_KEY = test_encryption_key
    settings.HMAC_KEY = test_hmac_key
    # Clear lru_cache to ensure new keys are loaded
    get_encryption_key.cache_clear()
    get_hmac_key.cache_clear()
    return settings


# ============================================================
# Performance Test Fixtures
# ============================================================


@pytest.fixture
@pytest.mark.slow
def large_product_dataset(tenant_context, product_category):
    """Create 10k products for performance testing."""
    from apps.inventario.models import Product

    products = []
    batch_size = 1000

    # Create products in batches to avoid memory issues
    for i in range(10000):
        product = Product(
            tenant=tenant_context,
            sku=f"PERF-{i:06d}",
            barcode=f"{7890000000000 + i}",
            name=f"Performance Test Product {i}",
            description=f"Product for performance testing batch {i // batch_size}",
            category=product_category,
            unit_price=Decimal("100.000"),
            cost_price=Decimal("50.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        )
        products.append(product)

        # Bulk create every 1000 products
        if (i + 1) % batch_size == 0:
            Product.objects.bulk_create(products)
            products = []

    # Create any remaining products
    if products:
        Product.objects.bulk_create(products)

    return Product.objects.filter(tenant=tenant_context, sku__startswith="PERF-")


@pytest.fixture
def multi_branch_setup(tenant_context):
    """Create 5 branches per tenant for multi-branch testing."""
    branches = []
    for i in range(1, 6):
        branch = Branch.objects.create(
            tenant=tenant_context,
            name=f"Branch {i}",
            address=f"{100 + i} Street {i}, Buenos Aires",
            phone=f"+54-11-{4000 + i}-{5000 + i}",
            afip_pos_number=i,
            is_active=True,
        )
        branches.append(branch)

    return branches


@pytest.fixture
def concurrent_operations_setup(tenant_context, product, branch):
    """
    Setup for concurrent stock operation tests.

    Creates initial stock and returns data for simulating concurrent operations.
    """
    from apps.inventario.models import StockMovement, StockSnapshot

    # Create initial stock
    initial_movement = StockMovement.objects.create(
        tenant=tenant_context,
        product=product,
        branch=branch,
        type=StockMovement.MovementType.PURCHASE,
        quantity_delta=Decimal("1000.0000"),
        cost_snapshot=product.cost_price,
        reference_id=uuid.uuid4(),
        notes="Initial stock for concurrent test",
    )

    # Create snapshot
    snapshot, _ = StockSnapshot.objects.get_or_create(
        product=product, branch=branch, defaults={"quantity": Decimal("1000.0000")}
    )

    return {
        "tenant": tenant_context,
        "product": product,
        "branch": branch,
        "initial_movement": initial_movement,
        "snapshot": snapshot,
        "initial_quantity": Decimal("1000.0000"),
    }


# ============================================================
# Markers
# ============================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies, SQLite-compatible)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "security: marks tests as security-focused tests")
    config.addinivalue_line(
        "markers",
        "performance: marks tests as performance tests (requires --run-performance flag)",
    )
    config.addinivalue_line(
        "markers", "concurrent: marks tests as testing concurrent operations"
    )
    config.addinivalue_line("markers", "docker: marks tests as Docker integration tests")
    config.addinivalue_line("markers", "property: marks tests as property-based tests")
    config.addinivalue_line("markers", "load: marks tests as load tests")
    config.addinivalue_line("markers", "fuzz: marks tests as API fuzzing tests")
    config.addinivalue_line("markers", "traceability: marks tests as traceability tests")
    config.addinivalue_line("markers", "jwt: marks tests as JWT security tests")
    config.addinivalue_line("markers", "ratelimit: marks tests as rate limiting tests")
    config.addinivalue_line("markers", "encryption: marks tests as encryption tests")
    config.addinivalue_line("markers", "tenant_isolation: marks tests as tenant isolation tests")
    config.addinivalue_line("markers", "owasp: marks tests as OWASP compliance tests")
    config.addinivalue_line("markers", "accounts: marks tests as producer account tests")


def pytest_collection_modifyitems(config, items):
    """Auto-skip docker-marked tests when Docker services are not available."""
    import os

    if os.environ.get("RUN_DOCKER_TESTS", "").lower() in ("1", "true", "yes"):
        return

    skip_docker = pytest.mark.skip(
        reason="Docker tests skipped (set RUN_DOCKER_TESTS=1 to enable)"
    )
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip_docker)


# ============================================================
# Security Test Fixtures
# ============================================================


@pytest.fixture
def jwt_attack_vectors():
    """Fixture providing JWT attack test vectors."""
    from tests.fixtures.security import JWT_ATTACK_VECTORS
    return JWT_ATTACK_VECTORS


@pytest.fixture
def rate_limit_test_cases():
    """Fixture providing rate limit test cases."""
    from tests.fixtures.security import RATE_LIMIT_TEST_CASES
    return RATE_LIMIT_TEST_CASES


@pytest.fixture
def cross_tenant_test_cases():
    """Fixture providing cross-tenant access test cases."""
    from tests.fixtures.security import CROSS_TENANT_TEST_CASES
    return CROSS_TENANT_TEST_CASES


@pytest.fixture
def owasp_injection_payloads():
    """Fixture providing OWASP injection test payloads."""
    from tests.fixtures.security import OWASP_INJECTION_PAYLOADS
    return OWASP_INJECTION_PAYLOADS


@pytest.fixture
def encryption_test_cases():
    """Fixture providing encryption test cases."""
    from tests.fixtures.security import ENCRYPTION_TEST_CASES
    return ENCRYPTION_TEST_CASES


# ============================================================
# Docker Test Fixtures
# ============================================================


@pytest.fixture(scope="session")
def docker_compose_file():
    """Fixture for Docker Compose file path."""
    return "docker-compose.test.yml"


@pytest.fixture
def health_check_endpoints():
    """Fixture providing health check endpoint configuration."""
    from tests.fixtures.docker_models import HEALTH_CHECK_ENDPOINTS
    return HEALTH_CHECK_ENDPOINTS


@pytest.fixture
def expected_network_topology():
    """Fixture providing expected network topology."""
    from tests.fixtures.docker_models import EXPECTED_NETWORK_TOPOLOGY
    return EXPECTED_NETWORK_TOPOLOGY


@pytest.fixture
def docker_services_config():
    """Fixture providing Docker services configuration."""
    from tests.fixtures.docker_models import DOCKER_SERVICES_CONFIG
    return DOCKER_SERVICES_CONFIG


# ============================================================
# Load Test Fixtures
# ============================================================


@pytest.fixture
def load_test_profiles():
    """Fixture providing load test profiles."""
    from tests.fixtures.load_models import LOAD_TEST_PROFILES
    return LOAD_TEST_PROFILES


@pytest.fixture
def endpoint_weights():
    """Fixture providing endpoint weight distribution."""
    from tests.fixtures.load_models import ENDPOINT_WEIGHTS
    return ENDPOINT_WEIGHTS


# ============================================================
# Fuzz Test Fixtures
# ============================================================


@pytest.fixture
def schemathesis_config():
    """Fixture providing Schemathesis configuration."""
    from tests.fixtures.fuzz_models import DEFAULT_SCHEMATHESIS_CONFIG
    return DEFAULT_SCHEMATHESIS_CONFIG


@pytest.fixture
def fuzz_target_endpoints():
    """Fixture providing fuzz target endpoints."""
    from tests.fixtures.fuzz_models import FUZZ_TARGET_ENDPOINTS
    return FUZZ_TARGET_ENDPOINTS


@pytest.fixture
def edge_case_payloads():
    """Fixture providing edge case payloads for fuzzing."""
    from tests.fixtures.fuzz_models import EDGE_CASE_PAYLOADS
    return EDGE_CASE_PAYLOADS


# ============================================================
# Traceability Fixtures
# ============================================================
# Note: traceability_matrix fixture is defined in tests/traceability/conftest.py
# with full implementation including test directory scanning


@pytest.fixture
def requirement_test_map():
    """Fixture providing requirement-to-test mapping."""
    from tests.fixtures.traceability_models import REQUIREMENT_TEST_MAP
    return REQUIREMENT_TEST_MAP


# ============================================================
# Security Test Fixture Aliases (for mass assignment tests)
# ============================================================


@pytest.fixture
def test_tenant(tenant_context):
    """Alias for tenant_context fixture for security tests."""
    return tenant_context


@pytest.fixture
def test_user(admin_user):
    """Alias for admin_user fixture for security tests."""
    return admin_user


@pytest.fixture
def other_user(sales_user):
    """Alias for sales_user as 'other_user' for security tests."""
    return sales_user


@pytest.fixture
def test_product(product):
    """Alias for product fixture for security tests."""
    return product


@pytest.fixture
def test_products(tenant_context, product_category):
    """Create multiple test products for bulk operation tests."""
    from apps.inventario.models import Product
    from decimal import Decimal

    products = []
    for i in range(5):
        products.append(Product.objects.create(
            tenant=tenant_context,
            sku=f"BULK-TEST-{i:03d}",
            name=f"Bulk Test Product {i}",
            category=product_category,
            unit_price=Decimal("100.000"),
            cost_price=Decimal("50.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        ))
    return products


@pytest.fixture
def other_product(other_tenant_product):
    """Alias for other_tenant_product for security tests."""
    return other_tenant_product


# ============================================================
# Coverage Enforcement (T128)
# ============================================================


# Critical modules requiring 95% coverage (FR-026)
CRITICAL_MODULES = [
    "apps.auth",
    "apps.core.encryption",
    "apps.core.middleware",
    "apps.inventario.views",
]

# Standard modules requiring 80% coverage
STANDARD_COVERAGE_THRESHOLD = 80
CRITICAL_COVERAGE_THRESHOLD = 95


def pytest_sessionfinish(session, exitstatus):
    """
    Post-session hook to validate coverage thresholds.

    This hook runs after all tests complete and validates that:
    - Overall coverage meets the standard threshold (80%)
    - Critical modules meet the elevated threshold (95%)

    Note: Actual coverage enforcement is done via pytest-cov CLI flags.
    This hook provides additional visibility into coverage failures.
    """
    # Only run coverage validation if coverage was collected
    if not hasattr(session.config, "_cov"):
        return

    # Get the coverage data if available
    cov = getattr(session.config, "_cov", None)
    if cov is None:
        return

    # Report any critical module coverage concerns
    terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminal_reporter:
        terminal_reporter.write_line("")
        terminal_reporter.write_line("=" * 70)
        terminal_reporter.write_line("COVERAGE ENFORCEMENT CHECK")
        terminal_reporter.write_line("=" * 70)
        terminal_reporter.write_line(
            f"Critical modules ({CRITICAL_COVERAGE_THRESHOLD}% required):"
        )
        for module in CRITICAL_MODULES:
            terminal_reporter.write_line(f"  - {module}")
        terminal_reporter.write_line(
            f"Standard threshold: {STANDARD_COVERAGE_THRESHOLD}%"
        )
        terminal_reporter.write_line("=" * 70)
