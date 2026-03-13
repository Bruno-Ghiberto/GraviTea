# Session: Test Fixes for Tenant Isolation - 2025-11-27

## Session Summary
Successfully fixed all remaining test failures in GRAVITEA-ERP backend. Final result: **224 tests passing**.

## Key Issues Resolved

### 1. User Tenant Isolation Bug
**Location**: `apps/auth/views.py:109`
**Problem**: `UserViewSet.get_queryset()` didn't filter by tenant because `AppUserManager` extends Django's `BaseUserManager` instead of `TenantBoundManager`.
**Solution**: Added explicit tenant filtering:
```python
def get_queryset(self):
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValueError("Tenant context not set")
    return User.objects.filter(tenant_id=tenant_id).select_related('role', 'default_branch')
```

### 2. Sync Endpoint Tenant Isolation Tests
**Location**: `tests/sync/test_sync_endpoints.py`
**Problem 1**: Creating objects for `other_tenant` failed because `TenantBoundModel.save()` triggers `full_clean()` which queries using `TenantBoundManager`.
**Solution**: Set tenant context before creating objects:
```python
set_current_tenant_id(other_tenant.id)
Branch.objects.create(tenant=other_tenant, ...)
SyncSession.objects.create(tenant=other_tenant, ...)
set_current_tenant_id(tenant.id)  # Restore original
```

**Problem 2**: `other_tenant_client` fixture shared same `api_client` as `authenticated_client`, overwriting auth credentials.
**Solution**: Removed `other_tenant_client` from test parameters.

## Important Patterns Discovered

### TenantBoundModel Save Behavior
When saving tenant-bound models:
1. `save()` calls `full_clean()` which validates unique constraints
2. Unique validation queries the database using `TenantBoundManager`
3. `TenantBoundManager.get_queryset()` requires tenant context
4. **Always set tenant context before creating objects, even with `all_objects`**

### Fixture Conflicts
- `api_client` fixture is shared by default
- `authenticated_client` and `other_tenant_client` both use same `api_client`
- Later fixture overwrites credentials of earlier one
- **Solution**: Don't use both fixtures in same test, or use separate client instances

### Custom Manager Pattern for User Model
- Django's `AbstractBaseUser` requires `BaseUserManager` for `create_user()` / `create_superuser()`
- Cannot simply inherit from `TenantBoundManager`
- **Pattern**: Keep `AppUserManager(BaseUserManager)` but filter explicitly in views

## Files Modified
1. `apps/auth/views.py` - Added tenant filtering to UserViewSet
2. `tests/sync/test_sync_endpoints.py` - Fixed tenant context and removed conflicting fixture

## Test Results
- Auth tests: 15 passing
- Core tests: 44 passing (10 tenant isolation + 34 encryption)
- Inventory tests: 28 passing
- Sync tests: 69 passing (23 endpoints + 46 models)
- Integration tests: 25 passing
- Performance tests: 8 passing
- **Total: 224 tests passing**

## Continuation Notes
- All tests pass without coverage requirement (80% coverage target needs more tests)
- RLS_CONTEXT_FAILURE warnings are expected on SQLite (PostgreSQL-specific RLS)
- Performance tests use simplified `reset_queries()` pattern for Python 3.14 compatibility
