# Auth Module

The `auth` module provides authentication, authorization, and multi-tenant user management for GRAVITEA ERP.

## Directory Structure

```
apps/auth/
├── migrations/          # Database migrations
├── models.py            # Tenant, Branch, AppUser models
├── serializers.py       # DRF serializers for auth endpoints
├── views.py             # ViewSets for auth API
├── admin.py             # Django admin configuration
└── apps.py              # Django app configuration
```

## Key Models

### Tenant

Root entity for multi-tenant isolation:

```python
class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Branch

Physical locations within a tenant:

```python
class Branch(TenantBoundModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)  # Unique within tenant
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```

### AppUser

Custom user model with tenant/branch association:

```python
class AppUser(AbstractBaseUser, TenantBoundModel):
    email = models.EmailField(unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
```

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login/` | POST | Obtain JWT tokens |
| `/api/v1/auth/refresh/` | POST | Refresh access token |
| `/api/v1/auth/logout/` | POST | Blacklist refresh token |

### Users

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/users/` | GET | List tenant users |
| `/api/v1/auth/users/` | POST | Create new user |
| `/api/v1/auth/users/{id}/` | GET | Get user details |
| `/api/v1/auth/users/{id}/` | PATCH | Update user |
| `/api/v1/auth/users/me/` | GET | Current user profile |

### Branches

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/branches/` | GET | List tenant branches |
| `/api/v1/auth/branches/` | POST | Create new branch |
| `/api/v1/auth/branches/{id}/` | GET | Get branch details |
| `/api/v1/auth/branches/{id}/` | PATCH | Update branch |

## Authentication Flow

### Login Request

```http
POST /api/v1/auth/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword"
}
```

### Response

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 123,
        "email": "user@example.com",
        "tenant_id": 1,
        "branch_id": 5,
        "role": "admin"
    }
}
```

### JWT Token Claims

```json
{
    "user_id": 123,
    "tenant_id": 1,
    "branch_id": 5,
    "role": "admin",
    "exp": 1735689600,
    "iat": 1735686000
}
```

## Security Features

### Password Requirements

- Minimum 8 characters
- Must contain uppercase and lowercase
- Must contain numbers
- Must contain special characters

### Rate Limiting

Login endpoint is rate-limited to prevent brute force:

- 5 failed attempts: 5-minute lockout
- 10 failed attempts: 30-minute lockout
- 20 failed attempts: Account locked (admin unlock required)

### Security Logging (SC-022)

All authentication events are logged:

```python
# Failed login attempt
logger.warning("Failed login attempt", extra={
    "email": email,
    "ip_address": request.META.get("REMOTE_ADDR"),
    "user_agent": request.META.get("HTTP_USER_AGENT"),
})
```

### Security Alerts (SC-023)

Real-time alerts for security events:

```python
from apps.core.observability import security_alert

security_alert(
    event_type="failed_auth",
    ip_address=request.META.get("REMOTE_ADDR"),
    user_identifier=email,
    context={"attempts": failed_count}
)
```

## User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Tenant administrator | Full access |
| `manager` | Branch manager | Branch operations |
| `cashier` | POS operator | Sales, limited inventory |
| `inventory` | Stock manager | Full inventory access |
| `readonly` | View only | Read-only access |

## Multi-Tenant Isolation

### Automatic Filtering

All queries are automatically filtered by tenant:

```python
# This returns only users in the current tenant
users = AppUser.objects.all()  # Already filtered by TenantBoundManager
```

### IDOR Prevention

Cross-tenant access attempts are blocked and logged:

```python
# Attempting to access another tenant's branch raises PermissionDenied
branch = Branch.objects.get(id=other_tenant_branch_id)  # Blocked
```

## Configuration

### Django Settings

```python
AUTH_USER_MODEL = 'auth.AppUser'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'TOKEN_OBTAIN_SERIALIZER': 'apps.auth.serializers.TenantTokenObtainPairSerializer',
}
```

## Testing

```bash
# Run auth module tests
pytest apps/auth/tests/ -v

# Test specific functionality
pytest apps/auth/tests/test_authentication.py -v
pytest apps/auth/tests/test_permissions.py -v
```

## Related Documentation

- [JWT Authentication](../../docs/authentication.md)
- [Security Architecture](../core/SECURITY.md)
- [API Contracts](../../../specs/001-backend-core/contracts/auth-api.yaml)
