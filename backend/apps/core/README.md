# Core Module

The `core` module provides foundational infrastructure for the GRAVITEA ERP system, including multi-tenant architecture, encryption, security, and observability.

## Directory Structure

```
apps/core/
├── encryption/          # AES-256-GCM encryption for PII fields
│   ├── __init__.py
│   ├── fields.py        # EncryptedCharField, EncryptedTextField
│   └── blind_index.py   # HMAC-SHA256 blind indexing for searchable encryption
├── managers/            # Custom Django model managers
│   └── tenant_manager.py  # TenantBoundManager with automatic filtering
├── middleware/          # Django middleware
│   └── tenant_middleware.py  # TenantContextMiddleware for multi-tenant
├── models/              # Core data models
│   └── tenant.py        # TenantBoundModel base class
├── observability/       # Monitoring and alerting (SC-021, SC-022, SC-023)
│   ├── __init__.py
│   ├── alerts.py        # Unified alerting for fiscal/sync/security
│   └── uptime.py        # Health checks and uptime monitoring (SC-014)
├── security/            # Security utilities
│   └── rate_limiter.py  # Rate limiting for API endpoints
├── authentication.py    # JWT authentication with tenant/branch claims
├── fields.py            # Custom model fields
├── pagination.py        # Cursor-based pagination (SC-015)
├── secrets.py           # Google Secret Manager integration
└── SECURITY.md          # Security documentation
```

## Key Components

### Multi-Tenant Architecture

All tenant-bound models inherit from `TenantBoundModel`:

```python
from apps.core.models.tenant import TenantBoundModel

class Product(TenantBoundModel):
    name = models.CharField(max_length=255)
    # Automatically scoped to tenant via TenantBoundManager
```

**Features:**
- Automatic tenant filtering via `TenantBoundManager`
- IDOR prevention with `_validate_tenant_references()`
- Async-safe context using `contextvars` (not `threading.local`)

### Encryption

AES-256-GCM encryption for PII fields with blind indexing:

```python
from apps.core.encryption.fields import EncryptedCharField

class Customer(TenantBoundModel):
    # Encrypted storage with searchable blind index
    email = EncryptedCharField(max_length=255, blind_index=True)
    phone = EncryptedCharField(max_length=50)
```

### Authentication

JWT authentication with custom claims:

```python
# Token payload includes:
{
    "user_id": 123,
    "tenant_id": 1,
    "branch_id": 5,
    "roles": ["admin", "inventory_manager"]
}
```

### Observability

Unified alerting per SC-021, SC-022, SC-023:

```python
from apps.core.observability import fiscal_alert, sync_alert, security_alert

# Fiscal service failure (SC-021)
fiscal_alert(
    service="afip",
    operation="invoice_emission",
    error="Connection timeout",
    tenant_id=tenant.id
)

# Sync failure with debug context (SC-022)
sync_alert(
    operation="push",
    branch_id=branch.id,
    error="Conflict resolution failed",
    context={"conflict_type": "price_update"}
)

# Security event (SC-023)
security_alert(
    event_type="failed_auth",
    ip_address="192.168.1.100",
    user_identifier="john@example.com"
)
```

### Health Monitoring

Uptime monitoring for SC-014 (99.9% availability):

```python
from apps.core.observability import get_uptime_monitor

monitor = get_uptime_monitor()
health = monitor.get_health()

if health.is_healthy:
    # System operational
    pass

# Check SLA compliance
if monitor.is_meeting_sla():
    # Meeting 99.9% uptime target
    pass
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENCRYPTION_KEY` | AES-256 encryption key (base64) | Required |
| `BLIND_INDEX_KEY` | HMAC key for blind indexing | Required |
| `ALERT_WEBHOOK_URL` | Webhook for alert delivery | None |
| `LOG_LEVEL` | Logging level | INFO |

### Django Settings

```python
# settings/base.py

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.core.authentication.TenantJWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.CursorPagination',
}
```

## Success Criteria Coverage

| Criterion | Description | Implementation |
|-----------|-------------|----------------|
| SC-014 | 99.9% uptime | `observability/uptime.py` |
| SC-021 | Fiscal alerts < 1 min | `observability/alerts.py` |
| SC-022 | Sync failure logging | `observability/alerts.py` |
| SC-023 | Security alerts | `observability/alerts.py` |

## Testing

```bash
# Run core module tests
pytest apps/core/tests/ -v

# Run with coverage
pytest apps/core/tests/ --cov=apps.core --cov-report=term-missing
```

## Related Documentation

- [Security Architecture](SECURITY.md)
- [API Authentication](../../docs/authentication.md)
- [Multi-Tenant Design](../../../specs/001-backend-core/research.md#multi-tenant-architecture)
