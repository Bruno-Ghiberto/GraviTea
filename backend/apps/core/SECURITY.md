# Security Documentation - Core Module

This document outlines security-critical information for the Gravitea ERP core module.

## Multi-Tenant Data Isolation

### Defense-in-Depth Architecture

Gravitea ERP implements a defense-in-depth approach to tenant data isolation:

1. **ORM Layer (TenantBoundManager)**: Automatically filters all queries by `tenant_id`
2. **Database Layer (PostgreSQL RLS)**: Row-Level Security policies enforce isolation at DB level
3. **IDOR Prevention (_validate_tenant_references)**: Validates FK references belong to same tenant

### Critical Security Functions

| Component | File | Purpose |
|-----------|------|---------|
| `TenantBoundManager` | `managers/tenant_bound.py` | Auto-filters queries by tenant |
| `set_current_tenant_id()` | `managers/tenant_bound.py` | Sets Python + PostgreSQL context |
| `_validate_tenant_references()` | `models/mixins.py` | IDOR prevention on FK writes |
| `TenantContextMiddleware` | `middleware/tenant_context.py` | Extracts tenant from JWT |
| `SecurityLogger` | `security/logging.py` | Structured security event logging |

---

## SECURITY WARNING: Bulk Operations Bypass Validation

### The Risk

**Bulk operations bypass `_validate_tenant_references()` validation**, which is the IDOR prevention mechanism. This creates a potential security gap if bulk operations are used with user-supplied data.

### Affected Operations

| Operation | Validation Status | Risk Level |
|-----------|-------------------|------------|
| `Model.objects.create()` | ✅ Validated | Safe |
| `model.save()` | ✅ Validated | Safe |
| `Model.objects.bulk_create()` | ❌ **NOT Validated** | HIGH |
| `Model.objects.bulk_update()` | ❌ **NOT Validated** | HIGH |
| `QuerySet.update()` | ❌ **NOT Validated** | HIGH |
| `QuerySet.delete()` | ⚠️ Partial (RLS only) | MEDIUM |

### Safe Usage Patterns

```python
# ✅ SAFE: Individual create (validates FK references)
product = Product.objects.create(
    tenant=tenant,
    supplier=supplier,  # Validated against tenant_id
    name="Widget",
)

# ✅ SAFE: Individual save (validates FK references)
product.supplier = other_supplier
product.save()  # Validates supplier.tenant_id == product.tenant_id

# ⚠️ DANGEROUS: Bulk create (NO FK validation)
# Only use with data you fully control (migrations, system imports)
Product.objects.bulk_create([
    Product(tenant=tenant, supplier=supplier1, name="A"),
    Product(tenant=tenant, supplier=supplier2, name="B"),
])

# ⚠️ DANGEROUS: Bulk update (NO FK validation)
Product.objects.filter(category=old_cat).update(supplier=new_supplier)
```

### Required Safeguards for Bulk Operations

If you MUST use bulk operations:

1. **Pre-validate all FK references manually**:
```python
# Before bulk_create, validate all FKs
for obj in objects_to_create:
    if obj.supplier.tenant_id != obj.tenant_id:
        raise ValueError("IDOR violation in bulk operation")
Product.objects.bulk_create(objects_to_create)
```

2. **Use only with system-controlled data**:
   - Database migrations
   - System seeding scripts
   - Admin-only batch operations

3. **Log all bulk operations**:
```python
from apps.core.security import log_bulk_operation_warning

log_bulk_operation_warning(
    model_name='Product',
    operation='bulk_create',
    count=len(objects),
    tenant_id=tenant.id,
)
```

### Future Improvements

- [ ] Override `bulk_create()` to include FK validation
- [ ] Override `bulk_update()` to include FK validation
- [ ] Add Django admin warnings for bulk operations
- [ ] Implement audit logging for all bulk operations

---

## Encryption (AES-256-GCM)

### PII Fields

All PII fields use AES-256-GCM encryption with HMAC-SHA256 blind indexing:

| Field Type | Encryption | Searchable |
|------------|------------|------------|
| `EncryptedCharField` | AES-256-GCM | No |
| `EncryptedTextField` | AES-256-GCM | No |
| `BlindIndexField` | HMAC-SHA256 | Yes (exact match) |

### Key Management

- **ENCRYPTION_KEY**: 32-byte key for AES-256-GCM (base64 encoded)
- **HMAC_KEY**: 32-byte key for blind indexing (base64 encoded)
- Keys loaded from Django settings (should come from Secret Manager in production)

### Generate Keys

```bash
python -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## Security Logging

### Log Levels by Event Type

| Event | Logger | Level | Action Required |
|-------|--------|-------|-----------------|
| IDOR_ATTEMPT | security | CRITICAL | Immediate investigation |
| AUTH_FAILURE | security | WARNING | Monitor for patterns |
| RLS_CONTEXT_FAILURE | security | WARNING | Check DB connectivity |
| UNSCOPED_ACCESS | security | INFO | Audit trail |
| TENANT_CONTEXT_SET | security | DEBUG | Normal operation |
| BULK_OPERATION | security | WARNING | Review justification |

### Production Logging Configuration

```python
# settings/production.py
LOGGING = {
    'version': 1,
    'handlers': {
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/gravitea/security.log',
            'formatter': 'json',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## Security Checklist

### Before Deployment

- [ ] Verify ENCRYPTION_KEY and HMAC_KEY are set from Secret Manager
- [ ] Verify PostgreSQL RLS policies are enabled
- [ ] Verify security logger is writing to persistent storage
- [ ] Verify JWT secret is rotated from development default
- [ ] Run `python manage.py check --deploy` for Django security checks

### Code Review Checklist

- [ ] No `all_objects` usage without explicit justification
- [ ] No `bulk_create/bulk_update` with user data without validation
- [ ] All new FK fields in TenantBoundModel validated by `_validate_tenant_references`
- [ ] All new PII fields use EncryptedCharField/EncryptedTextField
- [ ] Security-critical operations logged with SecurityLogger

---

## Contact

For security concerns, contact the security team immediately.
Do not commit security vulnerabilities to version control.
