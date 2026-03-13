# Gravitea ERP - Code Style and Conventions

## Python Code Style

### Formatting Tools
- **black** - Code formatter (line length default: 88)
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Static type checking

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_prefixed_with_underscore`

### Import Order (isort)
1. Standard library
2. Third-party packages
3. Django imports
4. Local app imports

Example:
```python
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from rest_framework import serializers

from apps.core.models import Tenant
from apps.inventario.models import Product
```

## Django Patterns

### Model Conventions
- UUID primary keys: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- Explicit `db_table` names in Meta
- Always include `help_text` for documentation
- Use `TenantBoundModel` mixin for tenant-scoped data
- Include both `objects` (TenantBoundManager) and `all_objects` (AllObjectsManager)

```python
class MyModel(TenantBoundModel):
    """
    Model docstring with clear description.
    
    Attributes:
        field_name: Description of field purpose
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="my_models")
    name = models.CharField(max_length=100, help_text="Human-readable name")
    
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()
    
    class Meta:
        db_table = "my_model"
        ordering = ["name"]
        verbose_name = "My Model"
        verbose_name_plural = "My Models"
    
    def __str__(self) -> str:
        return self.name
```

### View/Serializer Patterns
- DRF ViewSets preferred over function-based views
- Explicit `queryset` and `serializer_class` attributes
- Use `@extend_schema` decorators for API documentation
- RFC 7807 Problem Details for error responses

### Test Patterns
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use fixtures from `tests/conftest.py`
- Mark tests with appropriate markers (unit, integration, security, etc.)

```python
@pytest.mark.unit
class TestProductService:
    """Tests for ProductService."""
    
    def test_create_product_success(self, tenant_context, branch):
        """Test successful product creation."""
        # Arrange
        data = {...}
        
        # Act
        result = ProductService.create(data)
        
        # Assert
        assert result.name == data["name"]
```

## Type Hints

### Required for
- Function parameters
- Function return types
- Class attributes (when not obvious from default)

```python
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from apps.core.models import Tenant

def get_tenant_by_id(tenant_id: uuid.UUID) -> Optional["Tenant"]:
    """Retrieve tenant by ID."""
    ...
```

## Docstrings

### Module Docstrings
```python
"""
Module description - brief one-liner.

Extended description if needed.
"""
```

### Class Docstrings
```python
class MyClass:
    """
    One-line summary.
    
    Extended description if needed.
    
    Attributes:
        attr1: Description
        attr2: Description
    """
```

### Function Docstrings
```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValidationError: When validation fails
    """
```

## Security Patterns

### Encrypted Fields
Use `EncryptedCharField`, `EncryptedTextField` for PII data with `BlindIndexField` for searching.

### Tenant Isolation
- Always use `TenantBoundManager` for queries
- Include `tenant` FK in models
- Test with `tenant_context` fixture

### Authentication
- JWT Bearer tokens via `TenantAwareJWTAuthentication`
- Include `tenant_id` in token claims

## Logging

### Use Named Loggers
```python
import logging

logger = logging.getLogger("apps.mymodule")

logger.info("Operation completed", extra={
    "tenant_id": str(tenant.id),
    "operation": "create_product",
})
```

### Security Events
```python
security_logger = logging.getLogger("security")
security_logger.warning("Invalid login attempt", extra={
    "user_email": email,
    "ip_address": request.META.get("REMOTE_ADDR"),
})
```
