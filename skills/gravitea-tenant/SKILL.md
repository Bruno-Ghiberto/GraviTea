---
name: gravitea-tenant
description: >
  Multi-tenant isolation patterns with Defense in Depth strategy.
  Covers TenantBoundManager, PostgreSQL RLS, IDOR prevention,
  and cross-tenant query protection.
  Trigger: When creating tenant-aware models, writing queries, or
  implementing tenant isolation middleware.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Multi-Tenant Isolation Skill

This skill enforces **Defense in Depth** for tenant data isolation.
Any query that bypasses tenant filtering is a **Critical Vulnerability**.

## When to Use

- Creating new models that belong to a tenant
- Writing queries that access tenant data
- Implementing views that handle tenant context
- Adding ForeignKey relationships to tenant-bound models
- Reviewing code for cross-tenant data leakage
- Implementing IDOR (Insecure Direct Object Reference) prevention

---

## Defense in Depth Architecture

```
+------------------------------------------+
|  Layer 1: APPLICATION                    |
|  - TenantBoundManager (auto-filter)      |
|  - TenantMiddleware (context injection)  |
|  - Permission classes (DRF)              |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|  Layer 2: DATABASE                       |
|  - PostgreSQL Row Level Security (RLS)   |
|  - RLS policies per table                |
|  - Connection-level tenant context       |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|  Layer 3: VALIDATION                     |
|  - IDOR checks on every FK               |
|  - JWT tenant claim verification         |
|  - Explicit tenant_id in all queries     |
+------------------------------------------+
```

**Philosophy**: If one layer fails, the others still protect the data.

---

## Critical Patterns

### Pattern 1: TenantBoundModel (Base Class)

**Every model that belongs to a tenant MUST inherit from TenantBoundModel.**

```python
# apps/core/models/base.py
from django.db import models
from django.conf import settings
import uuid

class TenantBoundManager(models.Manager):
    """
    Manager that automatically filters by tenant.
    NEVER returns data from other tenants.
    """

    def get_queryset(self):
        from .context import get_current_tenant
        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs.none()  # Fail closed - no tenant = no data

    def unscoped(self):
        """
        Bypass tenant filter (admin/system operations ONLY).
        REQUIRES explicit justification in code review.
        """
        return super().get_queryset()


class TenantBoundModel(models.Model):
    """
    Abstract base for all tenant-scoped models.
    Provides automatic tenant filtering and validation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Default manager with tenant filtering
    objects = TenantBoundManager()

    # All objects (for admin/system use ONLY)
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Ensure tenant is set before saving."""
        if not self.tenant_id:
            from .context import get_current_tenant
            tenant = get_current_tenant()
            if tenant is None:
                raise ValueError("Cannot save TenantBoundModel without tenant context")
            self.tenant = tenant
        super().save(*args, **kwargs)
```

**Usage**:

```python
# apps/inventario/models.py
from apps.core.models.base import TenantBoundModel

class Product(TenantBoundModel):
    """Product model - automatically tenant-scoped."""
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                name="unique_product_sku_per_tenant",
            ),
        ]

# Queries are AUTOMATICALLY filtered by tenant
products = Product.objects.all()  # Only current tenant's products
```

---

### Pattern 2: Tenant Context Management

**Thread-local storage for request-scoped tenant context.**

```python
# apps/core/models/context.py
import threading
from contextvars import ContextVar
from typing import Optional

# Context variable for async-safe tenant storage
_current_tenant: ContextVar[Optional["Tenant"]] = ContextVar(
    "current_tenant", default=None
)

def get_current_tenant() -> Optional["Tenant"]:
    """Get the current tenant from context."""
    return _current_tenant.get()

def set_current_tenant(tenant: Optional["Tenant"]) -> None:
    """Set the current tenant in context."""
    _current_tenant.set(tenant)

class TenantContext:
    """Context manager for temporary tenant switching."""

    def __init__(self, tenant):
        self.tenant = tenant
        self.previous_tenant = None

    def __enter__(self):
        self.previous_tenant = get_current_tenant()
        set_current_tenant(self.tenant)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_tenant(self.previous_tenant)
```

**Middleware Integration**:

```python
# apps/core/middleware/tenant.py
from django.http import HttpRequest
from apps.core.models import Tenant
from apps.core.models.context import set_current_tenant

class TenantMiddleware:
    """
    Extract tenant from JWT claims and set context.
    MUST run after authentication middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        tenant = None

        # Extract tenant from authenticated user
        if hasattr(request, "user") and request.user.is_authenticated:
            tenant = getattr(request.user, "tenant", None)

        # Alternative: Extract from JWT claims directly
        if tenant is None and hasattr(request, "auth"):
            tenant_id = request.auth.get("tenant_id")
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                except Tenant.DoesNotExist:
                    pass

        set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            set_current_tenant(None)  # Clear after request

        return response
```

---

### Pattern 3: PostgreSQL Row Level Security (RLS)

**Database-level protection - even if application layer is bypassed.**

```sql
-- database/sql/rls_policies.sql

-- Enable RLS on tenant-bound tables
ALTER TABLE inventario_product ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventario_stockmovement ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation_policy ON inventario_product
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_policy ON inventario_stockmovement
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Force RLS for table owner (important!)
ALTER TABLE inventario_product FORCE ROW LEVEL SECURITY;
ALTER TABLE inventario_stockmovement FORCE ROW LEVEL SECURITY;
```

**Connection-level tenant setting**:

```python
# apps/core/db/tenant_router.py
from django.db import connection

def set_db_tenant_context(tenant_id: str) -> None:
    """
    Set tenant context at database connection level.
    Required for RLS policies to work.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SET app.current_tenant_id = %s",
            [str(tenant_id)]
        )

# In middleware, after setting application context:
if tenant:
    set_db_tenant_context(str(tenant.id))
```

---

### Pattern 4: IDOR Prevention (ForeignKey Validation)

**Every ForeignKey to a tenant-bound model MUST be validated.**

```python
# apps/core/validators.py
from django.core.exceptions import ValidationError
from apps.core.models.context import get_current_tenant

def validate_same_tenant(value, model_class):
    """
    Validate that the referenced object belongs to the same tenant.
    Prevents IDOR attacks via manipulated IDs.
    """
    tenant = get_current_tenant()
    if tenant is None:
        raise ValidationError("No tenant context available")

    try:
        obj = model_class.objects.get(pk=value)
    except model_class.DoesNotExist:
        raise ValidationError(f"{model_class.__name__} not found")

    if obj.tenant_id != tenant.id:
        # Log security event - potential attack
        logger.warning(
            "IDOR attempt detected",
            extra={
                "attempted_id": value,
                "object_tenant": str(obj.tenant_id),
                "request_tenant": str(tenant.id),
            }
        )
        raise ValidationError(f"{model_class.__name__} not found")  # Generic error

    return obj
```

**Serializer Integration**:

```python
# apps/inventario/serializers.py
from rest_framework import serializers
from apps.core.validators import validate_same_tenant

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "quantity", "price"]

    def validate_product_id(self, value):
        """Validate product belongs to same tenant."""
        from apps.inventario.models import Product
        product = validate_same_tenant(value, Product)
        return product.id
```

**View-Level IDOR Protection**:

```python
# apps/inventario/views.py
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from apps.core.models.context import get_current_tenant

class ProductViewSet(viewsets.ModelViewSet):
    """
    Product CRUD with automatic tenant isolation.
    """
    serializer_class = ProductSerializer

    def get_queryset(self):
        """
        TenantBoundManager already filters by tenant.
        This is defense in depth.
        """
        return Product.objects.all()

    def get_object(self):
        """
        Additional IDOR check on single object retrieval.
        """
        obj = super().get_object()

        # Defense in depth: verify tenant matches
        tenant = get_current_tenant()
        if obj.tenant_id != tenant.id:
            # Don't reveal that object exists
            raise NotFound("Product not found")

        return obj
```

---

### Pattern 5: Branch-Level Isolation (Optional)

**For organizations with multiple branches within a tenant.**

```python
# apps/core/models/base.py

class BranchBoundManager(TenantBoundManager):
    """
    Manager that filters by tenant AND branch.
    Use for branch-specific data (inventory, sales).
    """

    def get_queryset(self):
        from .context import get_current_tenant, get_current_branch
        qs = super().get_queryset()  # Already filtered by tenant
        branch = get_current_branch()
        if branch is not None:
            return qs.filter(branch=branch)
        return qs


class BranchBoundModel(TenantBoundModel):
    """
    Abstract base for branch-scoped models.
    Inherits tenant isolation, adds branch filtering.
    """
    branch = models.ForeignKey(
        "core.Branch",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        null=True,  # Null = visible to all branches in tenant
        blank=True,
    )

    objects = BranchBoundManager()

    class Meta:
        abstract = True
```

---

## Decision Tree

```
Creating a new model?
|-- Does it contain tenant-specific data?
|   |-- Yes -> Inherit from TenantBoundModel
|   |   |-- Does it have branch-specific data?
|   |   |   |-- Yes -> Inherit from BranchBoundModel
|   |   |   +-- No -> Use TenantBoundModel
|   +-- No -> Use standard Model (system tables only)
|
Adding a ForeignKey?
|-- Is target model TenantBoundModel?
|   |-- Yes -> Add IDOR validation in serializer
|   +-- No -> Standard FK validation
|
Writing a query?
|-- Using TenantBoundManager?
|   |-- Yes -> Automatic tenant filtering (safe)
|   +-- No -> DANGER: Must add explicit .filter(tenant=tenant)
|
Need to access all tenants' data?
|-- Are you in admin/system context?
|   |-- Yes -> Use Model.all_objects.all() with justification
|   +-- No -> FORBIDDEN - refactor your approach
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Bypassing TenantBoundManager

```python
# FORBIDDEN - Bypasses tenant filtering
Product.all_objects.filter(price__gt=100)

# CORRECT - Uses TenantBoundManager
Product.objects.filter(price__gt=100)
```

### Anti-Pattern 2: Missing IDOR Validation

```python
# FORBIDDEN - Trusts client-provided ID
def get_product(request, product_id):
    return Product.all_objects.get(id=product_id)  # IDOR vulnerability!

# CORRECT - Validates tenant ownership
def get_product(request, product_id):
    return Product.objects.get(id=product_id)  # TenantBoundManager filters
```

### Anti-Pattern 3: Cross-Tenant ForeignKey

```python
# FORBIDDEN - No tenant validation on FK
class Order(TenantBoundModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    # If customer.tenant != self.tenant, this is a data leak!

# CORRECT - Validate in clean() or serializer
class Order(TenantBoundModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        if self.customer_id and self.customer.tenant_id != self.tenant_id:
            raise ValidationError("Customer must belong to same tenant")
```

### Anti-Pattern 4: Leaking Tenant Info in Errors

```python
# FORBIDDEN - Reveals tenant mismatch
if product.tenant_id != request.user.tenant_id:
    raise PermissionDenied("Product belongs to another tenant")

# CORRECT - Generic error
if product.tenant_id != request.user.tenant_id:
    raise NotFound("Product not found")  # Attackers can't enumerate
```

---

## Testing Tenant Isolation

```python
# tests/security/test_tenant_isolation.py
import pytest
from django.test import TestCase
from apps.core.models.context import TenantContext

class TenantIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Tenant A")
        cls.tenant_b = Tenant.objects.create(name="Tenant B")

        with TenantContext(cls.tenant_a):
            cls.product_a = Product.objects.create(
                sku="SKU-A", name="Product A", price=10.00
            )

        with TenantContext(cls.tenant_b):
            cls.product_b = Product.objects.create(
                sku="SKU-B", name="Product B", price=20.00
            )

    def test_tenant_a_cannot_see_tenant_b_products(self):
        """Verify strict tenant isolation."""
        with TenantContext(self.tenant_a):
            products = list(Product.objects.all())
            assert len(products) == 1
            assert products[0].id == self.product_a.id

    def test_tenant_b_cannot_see_tenant_a_products(self):
        """Verify reverse isolation."""
        with TenantContext(self.tenant_b):
            products = list(Product.objects.all())
            assert len(products) == 1
            assert products[0].id == self.product_b.id

    def test_no_tenant_context_returns_empty(self):
        """Verify fail-closed behavior."""
        with TenantContext(None):
            products = list(Product.objects.all())
            assert len(products) == 0

    def test_idor_prevention(self):
        """Verify cross-tenant ID access is blocked."""
        with TenantContext(self.tenant_a):
            # Attempting to access tenant B's product
            with pytest.raises(Product.DoesNotExist):
                Product.objects.get(id=self.product_b.id)
```

---

## Developer Checklist

Before submitting any tenant-related code, verify:

- [ ] **Model Inheritance**: All tenant data models inherit from TenantBoundModel
- [ ] **Manager Usage**: Using `objects` (filtered), not `all_objects` (unfiltered)
- [ ] **IDOR Validation**: All ForeignKeys validated for same-tenant
- [ ] **Error Messages**: No tenant information leaked in error responses
- [ ] **Context Handling**: Tenant context properly set/cleared in middleware
- [ ] **RLS Policies**: Database RLS enabled for new tables
- [ ] **Test Coverage**: Cross-tenant access tests included
- [ ] **Audit Logging**: Security events logged for IDOR attempts

---

## Commands

```bash
# Run tenant isolation tests
cd backend && pytest tests/security/test_tenant_isolation.py -v

# Check for unfiltered queries (code audit)
cd backend && grep -r "all_objects" --include="*.py" apps/

# Verify RLS policies exist
psql -d gravitea -c "\d+ inventario_product" | grep "Policies"

# Test RLS from SQL
psql -d gravitea -c "SET app.current_tenant_id = 'tenant-uuid'; SELECT * FROM inventario_product;"
```

---

## Resources

- **Base Models**: See `apps/core/models/base.py` for TenantBoundModel
- **Context**: See `apps/core/models/context.py` for tenant context management
- **Middleware**: See `apps/core/middleware/tenant.py` for request handling
- **RLS SQL**: See `database/sql/rls_policies.sql` for PostgreSQL policies
- **Tests**: See `tests/security/test_tenant_isolation.py` for isolation tests

---

*Last updated: 2026-01-20*
*Security standard: Defense in Depth (3-layer)*
