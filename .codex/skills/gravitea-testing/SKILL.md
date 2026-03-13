---
name: gravitea-testing
description: >
  Pytest patterns, fixtures, markers, and test organization for Gravitea.
  Covers unit tests, integration tests, security tests, and performance tests.
  Trigger: When writing tests, creating fixtures, or reviewing test coverage.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Testing Skill

This skill establishes **mandatory testing standards** for all Gravitea code.
Every feature MUST have corresponding tests before merge.

## When to Use

- Writing new tests for any component
- Creating reusable fixtures
- Organizing test files and directories
- Adding test markers for categorization
- Setting up test isolation (database, cache, tenant)
- Writing security-focused tests
- Creating performance/load tests

---

## Test Organization

### Directory Structure

```
backend/tests/
|-- conftest.py                 # Root fixtures (tenant, user, auth)
|-- pytest.ini                  # Pytest configuration
|-- fixtures/                   # Shared fixture modules
|   |-- __init__.py
|   |-- auth.py                 # Auth fixtures (tokens, users)
|   |-- tenant.py               # Tenant/branch fixtures
|   |-- inventory.py            # Product, stock fixtures
|   +-- security.py             # Security test fixtures
|-- unit/                       # Fast, isolated unit tests
|   |-- conftest.py
|   |-- test_models.py
|   |-- test_serializers.py
|   +-- observability/
|       +-- test_metrics.py
|-- integration/                # Database integration tests
|   |-- conftest.py
|   |-- test_api_endpoints.py
|   +-- observability/
|       +-- test_business_metrics.py
|-- security/                   # Security-focused tests
|   |-- test_tenant_isolation.py
|   |-- test_jwt_attacks.py
|   |-- test_owasp.py
|   +-- test_rate_limiting.py
|-- load/                       # Performance tests
|   +-- test_sustained_load.py
|-- smoke/                      # Quick deployment validation
|   +-- test_deployment_readiness.py
+-- docker/                     # Container tests
    |-- test_health_checks.py
    +-- test_graceful_shutdown.py
```

### Naming Conventions

| Pattern | Description | Example |
|---------|-------------|---------|
| `test_*.py` | Test files | `test_models.py` |
| `Test*` | Test classes | `TestProductModel` |
| `test_*` | Test methods | `test_price_cannot_be_negative` |
| `*_fixture` | Fixture functions | `authenticated_client_fixture` |

---

## Critical Patterns

### Pattern 1: Fixture Hierarchy & Scopes

**Fixture Scopes** (understand when to use each):

| Scope | Lifecycle | Use Case |
|-------|-----------|----------|
| `function` | Per test (default) | Most fixtures, test isolation |
| `class` | Per test class | Shared setup across class methods |
| `module` | Per test file | Expensive setup shared in module |
| `session` | Entire test run | Database connections, one-time setup |

**Root Fixtures** (available to all tests):

```python
# tests/conftest.py
import pytest
from django.test import override_settings
from apps.core.models import Tenant, Branch
from apps.core.models.context import TenantContext

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Session-scoped database setup.
    Runs once per test session.
    """
    with django_db_blocker.unblock():
        # Create system-level data if needed
        pass

@pytest.fixture
def tenant(db) -> Tenant:
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Tenant",
        slug="test-tenant",
        is_active=True,
    )

@pytest.fixture
def branch(db, tenant) -> Branch:
    """Create a test branch within tenant."""
    return Branch.objects.create(
        tenant=tenant,
        name="Main Branch",
        code="MAIN",
    )

@pytest.fixture
def tenant_context(tenant):
    """
    Context manager that sets tenant for the test.
    Use this to simulate authenticated requests.
    """
    with TenantContext(tenant):
        yield tenant

@pytest.fixture
def user(db, tenant):
    """Create a test user within tenant."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )

@pytest.fixture
def authenticated_client(client, user):
    """Client with authenticated session."""
    client.force_login(user)
    return client

@pytest.fixture
def api_client():
    """DRF API test client."""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_api_client(api_client, user):
    """API client with JWT authentication."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
    )
    return api_client
```

### Pattern 2: Test Markers

**Configuration** (`pytest.ini` or `pyproject.toml`):

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = gravitea.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers

markers =
    unit: Fast tests without database
    integration: Tests requiring database
    security: Security-focused tests
    auth: Authentication tests
    tenant: Tenant isolation tests
    slow: Long-running tests (>5s)
    docker: Tests requiring Docker
    load: Performance/load tests
    smoke: Quick deployment validation
    asyncio: Async tests (requires pytest-asyncio)
```

**Usage**:

```python
# tests/unit/test_validators.py
import pytest
import sys

@pytest.mark.unit
class TestPriceValidator:
    def test_positive_price_is_valid(self):
        assert validate_price(10.00) is True

    def test_negative_price_is_invalid(self):
        # Use match parameter for precise exception validation
        with pytest.raises(ValidationError, match="Price must be positive"):
            validate_price(-10.00)


# tests/security/test_tenant_isolation.py
@pytest.mark.security
@pytest.mark.tenant
class TestTenantIsolation:
    @pytest.mark.django_db
    def test_cross_tenant_access_blocked(self, tenant_a, tenant_b):
        # ...


# Conditional skipping with skipif
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
def test_unix_file_permissions():
    """Skip on Windows where file permissions work differently."""
    # ...

@pytest.mark.skipif(
    not os.environ.get("REDIS_URL"),
    reason="Requires Redis connection"
)
def test_redis_integration():
    """Skip if Redis not available."""
    # ...
```

**Running by marker**:

```bash
# Run only unit tests
pytest -m "unit"

# Run security tests
pytest -m "security"

# Run integration but not slow
pytest -m "integration and not slow"

# Run everything except docker
pytest -m "not docker"
```

**Running by name pattern** (`-k` filter):

```bash
# Run tests containing "product" in the name
pytest -k "product"

# Run tests containing "create" OR "update"
pytest -k "create or update"

# Run tests containing "api" but NOT "slow"
pytest -k "api and not slow"

# Combine with markers
pytest -m "integration" -k "tenant"
```

---

### Pattern 3: Factory Pattern (factory_boy)

**Prefer factories over JSON fixtures.**

```python
# tests/fixtures/factories.py
import factory
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker()

class TenantFactory(DjangoModelFactory):
    class Meta:
        model = "core.Tenant"

    name = factory.Sequence(lambda n: f"Tenant {n}")
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-"))
    is_active = True


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "core.User"

    tenant = factory.SubFactory(TenantFactory)
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = "inventario.Product"

    tenant = factory.SubFactory(TenantFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    name = factory.Faker("product_name")
    price = factory.Faker(
        "pydecimal", left_digits=3, right_digits=2, positive=True
    )
    cost = factory.LazyAttribute(lambda o: o.price * factory.Faker("pyfloat", min_value=0.4, max_value=0.7).generate())
    stock_quantity = factory.Faker("random_int", min=0, max=1000)
    is_active = True


# Usage in tests
@pytest.mark.django_db
def test_product_creation():
    product = ProductFactory(price=100.00, cost=60.00)
    assert product.profit_margin == 40.00

@pytest.mark.django_db
def test_bulk_products():
    products = ProductFactory.create_batch(10)
    assert len(products) == 10
```

---

### Pattern 4: Database Test Isolation

**Use `@pytest.mark.django_db` correctly**:

```python
# tests/integration/test_api_endpoints.py
import pytest

@pytest.mark.django_db
class TestProductAPI:
    """
    Each test method gets a fresh database transaction.
    Data is rolled back after each test.
    """

    def test_list_products(self, authenticated_api_client, tenant_context):
        ProductFactory.create_batch(5, tenant=tenant_context)
        response = authenticated_api_client.get("/api/v1/products/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 5

    def test_create_product(self, authenticated_api_client, tenant_context):
        data = {"sku": "NEW-001", "name": "New Product", "price": "99.99"}
        response = authenticated_api_client.post("/api/v1/products/", data)
        assert response.status_code == 201


@pytest.mark.django_db(transaction=True)
class TestTransactionBehavior:
    """
    Use transaction=True ONLY when testing commit/rollback.
    This is SLOWER as it flushes the database.
    """

    def test_atomic_operation_rollback(self):
        # Test that partial failures rollback completely
        pass
```

---

### Pattern 5: Cache Isolation

**Prevent cache pollution between tests**:

```python
# tests/conftest.py
import pytest
from django.core.cache import cache

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()

@pytest.fixture
def mock_cache(mocker):
    """Mock cache for unit tests without Redis."""
    return mocker.patch("django.core.cache.cache")
```

**Test Settings**:

```python
# gravitea/settings/test.py
from .base import *

# Use in-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Use in-memory database for speed (optional)
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": ":memory:",
#     }
# }

# Disable throttling in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
}
```

---

### Pattern 6: Security Test Fixtures

```python
# tests/fixtures/security.py
import pytest
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.fixture
def expired_token(user):
    """Generate an expired JWT token."""
    from datetime import timedelta
    from django.utils import timezone

    token = RefreshToken.for_user(user)
    # Manually set expiration in the past
    token.set_exp(from_time=timezone.now() - timedelta(hours=1))
    return str(token.access_token)

@pytest.fixture
def forged_token():
    """Token signed with wrong key (attack simulation)."""
    import jwt
    payload = {
        "user_id": "fake-user-id",
        "tenant_id": "fake-tenant-id",
    }
    return jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

@pytest.fixture
def alg_none_token():
    """Token with alg:none (attack simulation)."""
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload = base64.urlsafe_b64encode(
        json.dumps({"user_id": "attacker", "role": "admin"}).encode()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}."

@pytest.fixture
def other_tenant_product(db):
    """Product belonging to a DIFFERENT tenant (for IDOR tests)."""
    other_tenant = TenantFactory(name="Other Tenant")
    return ProductFactory(tenant=other_tenant)
```

---

### Pattern 7: Test ID Format

**Use descriptive test IDs for traceability**:

```python
# tests/security/test_jwt_attacks.py
import pytest

@pytest.mark.security
@pytest.mark.auth
class TestJWTAttacks:
    """
    Test ID format: SEC-AUTH-{number}
    Maps to security requirements document.
    """

    @pytest.mark.parametrize("attack_token,expected_status", [
        pytest.param("alg_none", 401, id="SEC-AUTH-001-alg-none-rejected"),
        pytest.param("expired", 401, id="SEC-AUTH-002-expired-rejected"),
        pytest.param("forged", 401, id="SEC-AUTH-003-forged-signature-rejected"),
    ])
    def test_attack_tokens_rejected(
        self, api_client, attack_token, expected_status, request
    ):
        """Verify malicious tokens are rejected."""
        token = request.getfixturevalue(f"{attack_token}_token")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get("/api/v1/products/")
        assert response.status_code == expected_status
```

---

### Pattern 8: Async Tests

**For testing Django ASGI views and async functions.**

```python
# tests/integration/test_async_views.py
import pytest
from asgiref.sync import sync_to_async

@pytest.mark.asyncio
async def test_async_data_fetch():
    """Test async data fetching."""
    result = await async_fetch_data()
    assert result is not None
    assert "data" in result


@pytest.mark.asyncio
async def test_async_database_query(async_client, tenant):
    """Test async database operations."""
    # Use sync_to_async for Django ORM
    @sync_to_async
    def get_products():
        return list(Product.objects.filter(tenant=tenant))

    products = await get_products()
    assert isinstance(products, list)


@pytest.mark.asyncio
async def test_async_api_endpoint(async_client, user):
    """Test ASGI view endpoint."""
    response = await async_client.get("/api/v1/async-products/")
    assert response.status_code == 200


# Async fixture
@pytest.fixture
async def async_resource():
    """Async fixture for resources needing async setup."""
    resource = await create_async_resource()
    yield resource
    await cleanup_async_resource(resource)
```

**Configuration** (add to `pytest.ini`):

```ini
[pytest]
asyncio_mode = auto
```

---

### Pattern 9: Mocking Patterns

**Use mocking for external dependencies and isolation.**

```python
# tests/unit/test_services.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

class TestPaymentService:
    """Mock external payment provider."""

    def test_successful_payment(self):
        """Mock successful Stripe charge."""
        with patch("apps.payments.services.stripe_client") as mock_stripe:
            mock_stripe.Charge.create.return_value = {
                "id": "ch_123",
                "status": "succeeded",
                "amount": 9999,
            }

            result = process_payment(amount=99.99, token="tok_visa")

            assert result["status"] == "succeeded"
            mock_stripe.Charge.create.assert_called_once()

    def test_payment_failure(self):
        """Mock payment failure with side_effect."""
        with patch("apps.payments.services.stripe_client") as mock_stripe:
            mock_stripe.Charge.create.side_effect = PaymentError("Card declined")

            with pytest.raises(PaymentError, match="Card declined"):
                process_payment(amount=99.99, token="tok_declined")

    def test_multiple_return_values(self):
        """Mock with different returns on consecutive calls."""
        with patch("apps.external.api_client.fetch") as mock_fetch:
            mock_fetch.side_effect = [
                {"data": "first"},
                {"data": "second"},
                APIError("Rate limited"),
            ]

            assert fetch_data()["data"] == "first"
            assert fetch_data()["data"] == "second"
            with pytest.raises(APIError):
                fetch_data()


class TestAsyncMocking:
    """Mock async functions."""

    @pytest.mark.asyncio
    async def test_async_external_call(self):
        """Mock async external service."""
        with patch("apps.services.external_api.fetch_async", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok"}

            result = await fetch_external_data()

            assert result["status"] == "ok"
            mock.assert_awaited_once()


# Fixture-based mocking with pytest-mock
@pytest.fixture
def mock_email_service(mocker):
    """Reusable mock for email service."""
    mock = mocker.patch("apps.notifications.email.send_email")
    mock.return_value = {"message_id": "msg_123", "status": "sent"}
    return mock


def test_user_registration_sends_email(mock_email_service, db):
    """Test that registration triggers welcome email."""
    register_user(email="new@example.com", password="secure123")

    mock_email_service.assert_called_once_with(
        to="new@example.com",
        template="welcome",
    )


# Mock context manager
class TestContextManagerMocking:
    def test_mock_file_operations(self):
        """Mock file reading."""
        mock_data = "tenant_id,name\n1,Test Tenant"

        with patch("builtins.open", MagicMock()):
            with patch("builtins.open", return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=mock_data))),
                __exit__=MagicMock(return_value=False)
            )):
                result = import_tenants_from_csv("tenants.csv")
                assert len(result) == 1
```

**When to Mock vs When to Use Real Dependencies**:

| Scenario | Approach |
|----------|----------|
| External APIs (Stripe, AWS) | Always mock |
| Database queries | Use real DB with fixtures |
| File system | Mock for unit, real for integration |
| Time/dates | Mock `datetime.now()` |
| Environment variables | Use `monkeypatch` fixture |
| Cache | Mock for unit, real for integration |

---

## Decision Tree

```
Writing a new test?
|-- Is it testing pure logic (no DB, no I/O)?
|   |-- Yes -> @pytest.mark.unit (no django_db)
|   +-- No -> Continue
|
|-- Is it testing async code (ASGI views, async functions)?
|   |-- Yes -> @pytest.mark.asyncio + async def test_*
|   +-- No -> Continue
|
|-- Does it need database access?
|   |-- Yes -> @pytest.mark.django_db
|   |   |-- Does it test transactions?
|   |   |   |-- Yes -> @pytest.mark.django_db(transaction=True)
|   |   |   +-- No -> Default (faster)
|   +-- No -> Continue
|
|-- Does it need external service mocking?
|   |-- Yes -> Use patch/MagicMock (see Pattern 9)
|   +-- No -> Continue
|
|-- Is it security-related?
|   |-- Yes -> @pytest.mark.security + appropriate sub-marker
|   +-- No -> Continue
|
|-- Does it take >5 seconds?
|   |-- Yes -> @pytest.mark.slow
|   +-- No -> Continue
|
|-- Does it need Docker?
|   |-- Yes -> @pytest.mark.docker
|   +-- No -> Continue
|
|-- Should it be skipped in certain environments?
|   |-- Yes -> @pytest.mark.skipif(condition, reason="...")
|   +-- No -> Continue
|
+-- Add descriptive test ID for traceability
```

---

## Test Patterns by Category

### Unit Tests (Fast, Isolated)

```python
# tests/unit/test_validators.py
import pytest
from apps.core.validators import validate_sku

@pytest.mark.unit
class TestSKUValidator:
    def test_valid_sku_format(self):
        assert validate_sku("SKU-12345") is True

    def test_invalid_sku_too_short(self):
        with pytest.raises(ValidationError):
            validate_sku("SK")

    @pytest.mark.parametrize("sku,expected", [
        ("SKU-001", True),
        ("sku-001", True),  # Case insensitive
        ("", False),
        (None, False),
    ])
    def test_sku_validation_cases(self, sku, expected):
        if expected:
            assert validate_sku(sku) is True
        else:
            with pytest.raises(ValidationError):
                validate_sku(sku)
```

### Integration Tests (With Database)

```python
# tests/integration/test_product_api.py
import pytest
from rest_framework import status

@pytest.mark.integration
@pytest.mark.django_db
class TestProductCRUD:
    def test_create_product(self, authenticated_api_client, tenant_context):
        data = {
            "sku": "NEW-001",
            "name": "New Product",
            "price": "99.99",
            "cost": "49.99",
        }
        response = authenticated_api_client.post("/api/v1/products/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["sku"] == "NEW-001"

    def test_list_products_filtered_by_tenant(
        self, authenticated_api_client, tenant_context, other_tenant_product
    ):
        # Create product for current tenant
        ProductFactory(tenant=tenant_context)

        response = authenticated_api_client.get("/api/v1/products/")
        assert response.status_code == status.HTTP_200_OK

        # Should NOT include other tenant's product
        product_ids = [p["id"] for p in response.json()["results"]]
        assert str(other_tenant_product.id) not in product_ids
```

### Security Tests

```python
# tests/security/test_tenant_isolation.py
import pytest

@pytest.mark.security
@pytest.mark.tenant
@pytest.mark.django_db
class TestTenantIsolation:
    """SEC-TENANT: Verify complete tenant data isolation."""

    def test_cannot_access_other_tenant_product(
        self, authenticated_api_client, other_tenant_product
    ):
        """SEC-TENANT-001: Cross-tenant GET is blocked."""
        response = authenticated_api_client.get(
            f"/api/v1/products/{other_tenant_product.id}/"
        )
        assert response.status_code == 404  # Not 403 (don't reveal existence)

    def test_cannot_update_other_tenant_product(
        self, authenticated_api_client, other_tenant_product
    ):
        """SEC-TENANT-002: Cross-tenant PUT is blocked."""
        response = authenticated_api_client.put(
            f"/api/v1/products/{other_tenant_product.id}/",
            {"name": "Hacked!"},
        )
        assert response.status_code == 404

    def test_cannot_delete_other_tenant_product(
        self, authenticated_api_client, other_tenant_product
    ):
        """SEC-TENANT-003: Cross-tenant DELETE is blocked."""
        response = authenticated_api_client.delete(
            f"/api/v1/products/{other_tenant_product.id}/"
        )
        assert response.status_code == 404
```

---

## Commands

```bash
# Run all tests
cd backend && pytest

# Run with coverage
cd backend && pytest --cov=apps --cov-report=term-missing --cov-report=html

# Run specific markers
cd backend && pytest -m "unit"
cd backend && pytest -m "security"
cd backend && pytest -m "integration and not slow"

# Run specific test file
cd backend && pytest tests/security/test_tenant_isolation.py -v

# Run specific test class
cd backend && pytest tests/security/test_tenant_isolation.py::TestTenantIsolation -v

# Run specific test method
cd backend && pytest tests/security/test_tenant_isolation.py::TestTenantIsolation::test_cannot_access_other_tenant_product -v

# Run with parallel execution
cd backend && pytest -n auto

# Run with verbose output and no capture
cd backend && pytest -v -s

# Generate JUnit XML report
cd backend && pytest --junitxml=test_results.xml

# Run failed tests from last run
cd backend && pytest --lf

# Run tests by name pattern (-k filter)
cd backend && pytest -k "product"
cd backend && pytest -k "create or update"
cd backend && pytest -k "api and not slow"

# Run async tests only
cd backend && pytest -m "asyncio" -v

# Show test durations (find slow tests)
cd backend && pytest --durations=10
```

---

## Developer Checklist

Before submitting tests, verify:

- [ ] **Markers Applied**: Appropriate markers for test category
- [ ] **Fixtures Used**: Using shared fixtures, not duplicating setup
- [ ] **Isolation Verified**: Tests don't depend on execution order
- [ ] **Cache Cleared**: No cache pollution between tests
- [ ] **Tenant Context**: TenantContext used for tenant-aware tests
- [ ] **Descriptive Names**: Test names describe what's being tested
- [ ] **Edge Cases**: Happy path AND error paths covered
- [ ] **Security Tests**: New features have corresponding security tests
- [ ] **Async Tests**: ASGI views tested with `@pytest.mark.asyncio`
- [ ] **Mocking**: External dependencies properly mocked
- [ ] **Skip Conditions**: Platform/env-specific tests use `skipif`

---

## Resources

- **Root Conftest**: See `tests/conftest.py` for shared fixtures
- **Factories**: See `tests/fixtures/factories.py` for factory patterns
- **Security Fixtures**: See `tests/fixtures/security.py` for attack tokens
- **Markers**: See `pytest.ini` for marker definitions
- **Coverage**: See `htmlcov/index.html` after running with `--cov`
- **Async Support**: Requires `pytest-asyncio` package
- **Mocking**: `pytest-mock` for fixture-based mocking, `unittest.mock` for inline

---

*Last updated: 2026-01-20*
*Testing framework: pytest + pytest-django + pytest-asyncio*
