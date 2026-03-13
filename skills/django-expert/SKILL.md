---
name: django-expert
description: >
  The ultimate architectural manifesto for Django 5.2 enterprise development.
  Covers ORM internals, ASGI, composite primary keys, security hardening,
  advanced testing, and database performance tuning.
  Trigger: When creating Django models, views, migrations, or optimizing queries.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
  django_version: "5.2"
---

# Django 5.2 Enterprise Development Standards

This skill establishes **mandatory standards** for all Django development within Gravitea.
It enforces high-performance, secure, and maintainable architectural patterns.

## When to Use

- Creating or modifying Django models
- Writing views (CBV or FBV) and URL configurations
- Optimizing database queries and fixing N+1 problems
- Creating or reviewing migrations
- Configuring Django settings for production
- Writing tests with pytest-django
- Setting up ASGI/WSGI deployment

---

## Critical Patterns

### Pattern 1: Custom User Model (Immutable Rule)

**The Problem**: Changing the user model mid-project causes disastrous migration chains.

**The Mandate**: Define a custom user model **IMMEDIATELY** upon project initialization.

```python
# apps/core/models/user.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    """Custom user with tenant awareness and UUID primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
    )
    branch = models.ForeignKey(
        "core.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    password_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_user"
        indexes = [
            models.Index(fields=["tenant", "email"]),
        ]
```

**Settings Configuration**:

```python
# gravitea/settings/base.py
AUTH_USER_MODEL = "core.User"
```

**Reference Pattern**:

```python
# In runtime code - ALWAYS use get_user_model()
from django.contrib.auth import get_user_model
User = get_user_model()

# In ForeignKey definitions - use settings reference
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # NOT "auth.User"
        on_delete=models.CASCADE,
    )
```

---

### Pattern 2: AppConfig & Lifecycle Management

**Mandate**: All applications **MUST** use `AppConfig` in `apps.py`.

```python
# apps/inventario/apps.py
from django.apps import AppConfig

class InventarioConfig(AppConfig):
    name = "apps.inventario"
    default_auto_field = "django.db.models.BigAutoField"
    default = True  # Avoid explicit path in INSTALLED_APPS

    def ready(self):
        """
        Signal registration ONLY.
        DO NOT perform database queries here.
        """
        from . import signals  # noqa: F401
```

**Settings Structure** (Modular, Never Monolithic):

```
gravitea/settings/
|-- __init__.py      # Empty or imports default
|-- base.py          # Shared settings
|-- dev.py           # Development overrides
|-- test.py          # Test-specific settings
+-- prod.py          # Production hardening
```

```python
# gravitea/settings/base.py
from pathlib import Path
import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# CRITICAL: Never hardcode secrets
SECRET_KEY = env("DJANGO_SECRET_KEY")
SECRET_KEY_FALLBACKS = env.list("DJANGO_SECRET_KEY_FALLBACKS", default=[])

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
```

---

### Pattern 3: Query Optimization (N+1 Prevention)

**The Problem**: Loops causing repeated database hits.

**Diagnosis**: Inspect any loop over related objects.

```python
# BAD - N+1 queries (1 + N additional queries)
orders = Order.objects.all()
for order in orders:
    print(order.customer.name)  # Each access hits DB
    for item in order.items.all():  # Each access hits DB
        print(item.product.name)  # Each access hits DB

# GOOD - Optimized with select_related and prefetch_related
orders = Order.objects.select_related(
    "customer",  # ForeignKey - uses JOIN
).prefetch_related(
    "items",  # Reverse FK - separate query
    "items__product",  # Nested prefetch
).all()
```

**Advanced Prefetch with Filtering**:

```python
from django.db.models import Prefetch

# Prefetch only active items with their products
orders = Order.objects.prefetch_related(
    Prefetch(
        "items",
        queryset=OrderItem.objects.filter(
            is_active=True
        ).select_related("product"),
        to_attr="active_items",  # Access via order.active_items
    )
)
```

**QuerySet Optimization Methods**:

| Method | Use Case | Warning |
|--------|----------|---------|
| `select_related()` | ForeignKey, OneToOne | SQL JOIN - can be heavy |
| `prefetch_related()` | ManyToMany, Reverse FK | Separate query in Python |
| `only()` | Load specific fields | Deferred fields hit DB on access |
| `defer()` | Exclude large fields | Same as only() inverse |
| `iterator()` | Large result sets | Disables prefetching |
| `exists()` | Check if any match | Never use `len(qs) > 0` |
| `count()` | Get count | Never use `len(qs)` |

---

### Pattern 4: Database Constraints (DB > Python)

**Principle**: Enforce integrity at the database level, not Python.

```python
# apps/inventario/models.py
from django.db import models
from django.db.models import Q, F

class Product(models.Model):
    sku = models.CharField(max_length=50)
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Unique SKU per tenant (not globally)
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                name="unique_sku_per_tenant",
            ),
            # Conditional unique: only active products
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                condition=Q(is_active=True),
                name="unique_active_sku_per_tenant",
            ),
            # Business rule: price >= cost
            models.CheckConstraint(
                check=Q(price__gte=F("cost")),
                name="price_gte_cost",
            ),
            # Business rule: stock cannot be negative
            models.CheckConstraint(
                check=Q(stock_quantity__gte=0),
                name="stock_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "sku"]),
        ]
```

**Field Rules**:

| Field Type | null | blank | Reasoning |
|------------|------|-------|-----------|
| CharField | `False` | `True` | Avoid two empty states (None vs "") |
| TextField | `False` | `True` | Same as CharField |
| BooleanField | `False` | N/A | Use `null=True` only for "Unknown" state |
| ForeignKey | Depends | Depends | `null=True` if relationship optional |
| DateTimeField | Depends | Depends | Use `auto_now_add` for created_at |

---

### Pattern 5: Bulk Operations

**Warning**: Bulk operations **DO NOT** emit signals or call `save()`.

```python
# Bulk create - single INSERT statement
products = [
    Product(sku=f"SKU-{i}", tenant=tenant, price=10.00, cost=5.00)
    for i in range(1000)
]
Product.objects.bulk_create(
    products,
    batch_size=100,  # Insert in batches of 100
    ignore_conflicts=True,  # Skip duplicates
)

# Bulk update - single UPDATE statement
products = list(Product.objects.filter(tenant=tenant))
for p in products:
    p.price = p.price * 1.1  # 10% increase

Product.objects.bulk_update(
    products,
    fields=["price"],  # Only update specified fields
    batch_size=100,
)

# Bulk delete via queryset (no iteration)
Product.objects.filter(
    tenant=tenant,
    is_active=False,
    updated_at__lt=timezone.now() - timedelta(days=365),
).delete()
```

---

### Pattern 6: Asynchronous Views (ASGI)

**When to Use**: High-concurrency I/O-bound operations (external API calls).

**When NOT to Use**: CPU-bound operations or heavy ORM queries.

```python
# apps/sync/views.py
import httpx
from asgiref.sync import sync_to_async
from django.http import JsonResponse

async def fetch_external_data(request):
    """Async view for external API calls."""

    # Async HTTP client (non-blocking)
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.external.com/data")
        external_data = response.json()

    # ORM call wrapped with sync_to_async
    @sync_to_async
    def get_local_data():
        return list(Product.objects.filter(is_active=True).values("sku", "price"))

    local_data = await get_local_data()

    return JsonResponse({
        "external": external_data,
        "local": local_data,
    })
```

**Context Switching Warning**:

```python
# gravitea/settings/base.py

# For ASGI (async-heavy workload)
ASGI_APPLICATION = "gravitea.asgi.application"

# Middleware order matters - avoid sync/async mixing
MIDDLEWARE = [
    # Async-compatible middleware first
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ...
]
```

---

## Security Hardening

### Production Configuration Checklist

```python
# gravitea/settings/prod.py
from .base import *

# CRITICAL: Must be False in production
DEBUG = False

# Strict host validation
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookie security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content security
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Session engine (avoid filesystem)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
```

### SQL Injection Prevention

```python
# FORBIDDEN - String formatting in raw SQL
cursor.execute(f"SELECT * FROM products WHERE sku = '{user_input}'")  # NEVER!

# CORRECT - Parameterized queries
cursor.execute(
    "SELECT * FROM products WHERE sku = %s AND tenant_id = %s",
    [user_input, tenant_id],  # Parameters as list
)

# CORRECT - ORM with extra()
Product.objects.extra(
    where=["sku = %s"],
    params=[user_input],
)
```

### XSS Prevention

```python
# Template auto-escaping is ON by default
# AUDIT any usage of:
{{ data|safe }}           # Dangerous if data is untrusted
{% autoescape off %}      # Dangerous block
mark_safe(user_content)   # Only for truly trusted content

# SAFE - JSON output for JavaScript
{{ data|json_script:"my-data" }}
```

---

## Migration Management

### Safe Migration Workflow

```bash
# 1. Generate migration
python manage.py makemigrations app_name

# 2. ALWAYS review the SQL before applying
python manage.py sqlmigrate app_name 0001_initial

# 3. Apply migration
python manage.py migrate
```

### Adding Non-Nullable Field to Populated Table

```python
# Step 1: Add as nullable
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                "Category",
                on_delete=models.PROTECT,
                null=True,  # Temporarily nullable
            ),
        ),
    ]

# Step 2: Data migration to populate
def populate_category(apps, schema_editor):
    Product = apps.get_model("inventario", "Product")
    Category = apps.get_model("inventario", "Category")
    default_category = Category.objects.get_or_create(name="Uncategorized")[0]
    Product.objects.filter(category__isnull=True).update(category=default_category)

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(populate_category, migrations.RunPython.noop),
    ]

# Step 3: Make non-nullable
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                "Category",
                on_delete=models.PROTECT,
                null=False,  # Now non-nullable
            ),
        ),
    ]
```

---

## Testing Patterns

### Test Class Selection

| Class | Use Case | Speed |
|-------|----------|-------|
| `SimpleTestCase` | No database (utils, template tags) | Fastest |
| `TestCase` | Database with transaction rollback | Fast |
| `TransactionTestCase` | Test commit/rollback behavior | Slow |
| `LiveServerTestCase` | Selenium/Playwright E2E | Slowest |

### Optimized Test Setup

```python
# tests/inventario/test_models.py
import pytest
from django.test import TestCase

class ProductModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Called ONCE per class (not per test method).
        Use for read-only test data.
        """
        cls.tenant = Tenant.objects.create(name="Test Tenant")
        cls.category = Category.objects.create(
            tenant=cls.tenant,
            name="Electronics",
        )
        cls.product = Product.objects.create(
            tenant=cls.tenant,
            category=cls.category,
            sku="TEST-001",
            price=100.00,
            cost=50.00,
        )

    def test_profit_margin_calculation(self):
        """Test uses cls.product without recreating it."""
        assert self.product.profit_margin == 50.00

    def test_sku_uniqueness_per_tenant(self):
        """Test constraint enforcement."""
        with pytest.raises(IntegrityError):
            Product.objects.create(
                tenant=self.tenant,
                sku="TEST-001",  # Duplicate
                price=10.00,
                cost=5.00,
            )
```

### Factory Pattern (Preferred over Fixtures)

```python
# tests/factories.py
import factory
from factory.django import DjangoModelFactory

class TenantFactory(DjangoModelFactory):
    class Meta:
        model = "core.Tenant"

    name = factory.Sequence(lambda n: f"Tenant {n}")

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = "inventario.Product"

    tenant = factory.SubFactory(TenantFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    cost = factory.LazyAttribute(lambda o: o.price * 0.6)
```

---

## Decision Tree

```
Creating a new model?
|-- Does it belong to a tenant?
|   |-- Yes -> Inherit from TenantBoundModel
|   +-- No -> Use standard Model (rare)
|
|-- Does it have a ForeignKey?
|   |-- Yes -> Set appropriate on_delete:
|   |   |-- Parent deleted = child deleted? -> CASCADE
|   |   |-- Parent deleted = block? -> PROTECT
|   |   |-- Parent deleted = nullify? -> SET_NULL
|   +-- No -> Continue
|
|-- Does it need unique constraints?
|   |-- Yes -> Use UniqueConstraint (not unique=True on field)
|   +-- No -> Continue
|
|-- Does it have business rules?
|   |-- Yes -> Add CheckConstraint in Meta.constraints
|   +-- No -> Continue
|
+-- Add db_index to fields used in filter/order_by
```

---

## Developer Checklist

Before submitting any Django code, verify:

- [ ] **Custom User Model**: Using `get_user_model()` in code, `AUTH_USER_MODEL` in FK
- [ ] **Model Integrity**: `on_delete` set correctly, constraints defined
- [ ] **Query Efficiency**: `select_related`/`prefetch_related` applied
- [ ] **Migration Safety**: Reviewed with `sqlmigrate`, reversible
- [ ] **Security**: DEBUG=False, secrets in env vars, CSRF active
- [ ] **Test Coverage**: Using `setUpTestData`, factories over fixtures
- [ ] **Type Hints**: All functions annotated
- [ ] **Async Safety**: No blocking calls in async views

---

## Commands

```bash
# Run migrations
cd backend && python manage.py migrate

# Generate migration
cd backend && python manage.py makemigrations app_name

# Review migration SQL
cd backend && python manage.py sqlmigrate app_name 0001

# Squash migrations
cd backend && python manage.py squashmigrations app_name 0001 0010

# Check for issues
cd backend && python manage.py check --deploy

# Shell with ORM access
cd backend && python manage.py shell_plus --ipython

# Run all tests
cd backend && pytest

# Run with query logging
cd backend && pytest --ds=gravitea.settings.test -p no:warnings --tb=short
```

---

## Resources

- **Settings**: See `gravitea/settings/` for configuration modules
- **Models**: See `apps/core/models/` for base model patterns
- **Tests**: See `tests/` for pytest patterns and factories
- **Migrations**: See `apps/*/migrations/` for migration examples
- **Reference**: Django 5.2 Documentation, Two Scoops of Django

---

*Last updated: 2026-01-20*
*Django version: 5.2*
