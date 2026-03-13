---
name: gravitea-auth
description: >
  The definitive security manifesto for JWT authentication in Gravitea.
  Covers algorithm enforcement, vulnerability mitigation, token lifecycle,
  claim validation, and rate limiting patterns.
  Trigger: When editing apps/auth/, implementing login/logout, token refresh,
  or any JWT-related functionality.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
  source: JWT Handbook v0.14.2
---

# Gravitea Authentication Skill

This skill enforces **Best Current Practices (BCP)** for JWT/JWS/JWE implementation.
Any deviation is considered a **Critical Vulnerability (CVSS 9.0+)**.

## When to Use

- Editing `apps/auth/views.py` or `apps/auth/jwt.py`
- Implementing login, logout, or token refresh endpoints
- Configuring `djangorestframework-simplejwt` settings
- Adding rate limiting to authentication endpoints
- Handling token revocation or blacklisting
- Working with encrypted tokens (JWE) for PII

---

## Critical Patterns

### Pattern 1: Algorithm Whitelist Enforcement

**The Attack**: `alg: none` signature stripping or RSA-to-HMAC key confusion.

**Implementation**:

```python
# gravitea/settings/base.py
SIMPLE_JWT = {
    # CRITICAL: Explicit algorithm whitelist - NEVER trust header
    "ALGORITHM": "RS256",
    "SIGNING_KEY": env("JWT_PRIVATE_KEY"),
    "VERIFYING_KEY": env("JWT_PUBLIC_KEY"),

    # Block "none" and symmetric algorithms when using asymmetric
    "JWS_ALGORITHM": "RS256",  # Enforced, not dynamic

    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # Rotation for refresh tokens
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

**Verification Logic**:

```python
# apps/auth/jwt.py
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.exceptions import TokenError

ALLOWED_ALGORITHMS = frozenset(["RS256", "ES256", "PS256"])

def validate_algorithm(token_header: dict) -> None:
    """
    Reject tokens with forbidden algorithms.
    MUST be called BEFORE signature verification.
    """
    alg = token_header.get("alg", "").upper()

    if alg == "NONE":
        raise TokenError("Algorithm 'none' is forbidden")

    if alg not in ALLOWED_ALGORITHMS:
        raise TokenError(f"Algorithm '{alg}' not in whitelist")
```

---

### Pattern 2: Claim Validation Rules

**All registered claims MUST be validated**:

| Claim | Validation Rule | Gravitea Standard |
|-------|-----------------|-------------------|
| `iss` | **MUST** match auth server | `https://auth.gravitea.io` |
| `sub` | **MUST** be valid user UUID | UUIDv7 format |
| `aud` | **MUST** contain resource server | `gravitea-api` |
| `exp` | **MUST** reject if expired | Max 2 min clock skew |
| `nbf` | **MUST** reject if not yet valid | Check before use |
| `iat` | **MUST** be after last password reset | Revocation by policy |
| `jti` | **RECOMMENDED** for blacklisting | UUID for replay protection |

**Implementation**:

```python
# apps/auth/jwt.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings

class GraviteaTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer with tenant-aware claims."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add required claims
        token["iss"] = settings.JWT_ISSUER
        token["aud"] = settings.JWT_AUDIENCE
        token["tenant_id"] = str(user.tenant_id)
        token["branch_id"] = str(user.branch_id) if user.branch_id else None

        # Namespaced private claims (avoid collision)
        token["https://gravitea.io/claims/role"] = user.role
        token["https://gravitea.io/claims/permissions"] = list(user.get_permissions())

        return token
```

**Middleware Validation**:

```python
# apps/auth/middleware.py
from django.utils import timezone
from rest_framework_simplejwt.exceptions import InvalidToken

class ClaimValidationMiddleware:
    def validate_claims(self, payload: dict, user) -> None:
        # Issuer validation
        if payload.get("iss") != settings.JWT_ISSUER:
            raise InvalidToken("Invalid issuer")

        # Audience validation
        aud = payload.get("aud", [])
        if settings.JWT_AUDIENCE not in (aud if isinstance(aud, list) else [aud]):
            raise InvalidToken("Invalid audience")

        # iat revocation check (password change invalidates old tokens)
        token_iat = payload.get("iat", 0)
        if user.password_changed_at and token_iat < user.password_changed_at.timestamp():
            raise InvalidToken("Token issued before password change")
```

---

### Pattern 3: Secure Token Storage

**Mandate**: Prefer `HttpOnly; Secure; SameSite=Strict` cookies over localStorage.

**Why**: localStorage is accessible via JavaScript. XSS = token theft.

```python
# apps/auth/views.py
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

class CookieTokenObtainPairView(TokenObtainPairView):
    """Return tokens in secure HttpOnly cookies."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

            # Set HttpOnly cookies
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # HTTPS only
                samesite="Strict",  # CSRF protection
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="Strict",
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                path="/api/auth/refresh/",  # Limit scope
            )

            # Remove tokens from response body (security)
            del response.data["access"]
            del response.data["refresh"]

        return response
```

**CSRF Protection** (required when using cookies):

```python
# gravitea/settings/base.py
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
```

---

### Pattern 4: Key Strength Requirements

**Minimum Key Sizes** (per RFC 7518):

| Algorithm | Minimum Key Size | Gravitea Standard |
|-----------|------------------|-------------------|
| HS256 | 256 bits (32 bytes) | **Forbidden for APIs** |
| HS384 | 384 bits (48 bytes) | **Forbidden for APIs** |
| HS512 | 512 bits (64 bytes) | **Forbidden for APIs** |
| RS256 | 2048 bits | 4096 bits preferred |
| ES256 | 256 bits (P-256 curve) | Allowed for mobile |
| PS256 | 2048 bits | Preferred for high security |

**Key Generation**:

```bash
# Generate RS256 key pair (4096 bits)
openssl genrsa -out jwt_private.pem 4096
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

# Generate ES256 key pair (P-256 curve)
openssl ecparam -name prime256v1 -genkey -noout -out jwt_ec_private.pem
openssl ec -in jwt_ec_private.pem -pubout -out jwt_ec_public.pem
```

**Key Validation at Startup**:

```python
# apps/auth/apps.py
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from cryptography.hazmat.primitives import serialization

class AuthConfig(AppConfig):
    name = "apps.auth"

    def ready(self):
        self._validate_jwt_keys()

    def _validate_jwt_keys(self):
        from django.conf import settings

        private_key = settings.SIMPLE_JWT.get("SIGNING_KEY", "")

        if not private_key or len(private_key) < 100:
            raise ImproperlyConfigured(
                "JWT_PRIVATE_KEY is missing or too short. "
                "RSA keys must be at least 2048 bits."
            )

        # Verify it's a valid PEM key
        try:
            serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
            )
        except Exception as e:
            raise ImproperlyConfigured(f"Invalid JWT private key: {e}")
```

---

### Pattern 5: Rate Limiting for Auth Endpoints

**Critical**: Auth endpoints are prime targets for brute force attacks.

```python
# apps/core/rate_limiter.py
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle

class AuthRateThrottle(SimpleRateThrottle):
    """
    Strict rate limiting for authentication endpoints.
    5 attempts per minute per IP + username combination.
    """
    scope = "auth"

    def get_cache_key(self, request, view):
        # Combine IP and username for granular limiting
        ident = self.get_ident(request)
        username = request.data.get("username", "anonymous")
        return f"throttle_auth_{ident}_{username}"


class LoginAttemptTracker:
    """Track failed login attempts for account lockout."""

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_DURATION = 900  # 15 minutes

    @classmethod
    def record_failure(cls, username: str, ip: str) -> bool:
        """Record failed attempt. Returns True if account is now locked."""
        key = f"login_failures_{username}"
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, cls.LOCKOUT_DURATION)

        if attempts >= cls.LOCKOUT_THRESHOLD:
            cache.set(f"locked_{username}", True, cls.LOCKOUT_DURATION)
            # Log security event (never log password)
            logger.warning(
                "Account locked due to failed attempts",
                extra={"username": username, "ip": ip, "attempts": attempts}
            )
            return True
        return False

    @classmethod
    def is_locked(cls, username: str) -> bool:
        return cache.get(f"locked_{username}", False)

    @classmethod
    def clear_on_success(cls, username: str) -> None:
        cache.delete(f"login_failures_{username}")
        cache.delete(f"locked_{username}")
```

---

## Decision Tree

```
Authentication request received?
|-- Is algorithm in whitelist?
|   |-- No -> REJECT (401) "Invalid algorithm"
|   +-- Yes -> Continue
|
|-- Is token signature valid?
|   |-- No -> REJECT (401) "Invalid signature"
|   +-- Yes -> Continue
|
|-- Are all claims valid (iss, aud, exp, nbf)?
|   |-- No -> REJECT (401) "Invalid claims"
|   +-- Yes -> Continue
|
|-- Is token in blacklist (jti check)?
|   |-- Yes -> REJECT (401) "Token revoked"
|   +-- No -> Continue
|
|-- Is iat > user.password_changed_at?
|   |-- No -> REJECT (401) "Token invalidated"
|   +-- Yes -> Continue
|
|-- Is tenant_id in token == user.tenant_id?
|   |-- No -> REJECT (403) "Tenant mismatch"
|   +-- Yes -> GRANT ACCESS
```

---

## Token Lifecycle & Revocation

### Strategy 1: Short-Lived Access + Refresh Tokens

```python
# gravitea/settings/base.py
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Strategy 2: JTI Blacklist (Redis)

```python
# apps/auth/revocation.py
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken

def revoke_token(token: RefreshToken) -> None:
    """Add token to blacklist until expiration."""
    jti = token.payload.get("jti")
    exp = token.payload.get("exp")
    ttl = exp - int(timezone.now().timestamp())

    if ttl > 0:
        cache.set(f"blacklist_{jti}", True, ttl)

def is_token_revoked(jti: str) -> bool:
    """Check if token is in blacklist."""
    return cache.get(f"blacklist_{jti}", False)
```

### Strategy 3: iat Revocation (Password Change)

```python
# apps/auth/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def on_user_login(sender, user, request, **kwargs):
    """Clear login failures on successful authentication."""
    LoginAttemptTracker.clear_on_success(user.username)

# In User model
class User(AbstractUser):
    password_changed_at = models.DateTimeField(null=True, blank=True)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()
```

---

## Security Logging Rules

**NEVER log**:
- Full JWT tokens
- Passwords (even hashed)
- Secret keys

**ALWAYS log**:
- `jti` (JWT ID)
- `sub` (User ID)
- IP address
- Action (login, logout, refresh, revoke)
- Timestamp

```python
# apps/auth/logging.py
import structlog

logger = structlog.get_logger("auth")

def log_auth_event(event: str, user_id: str, jti: str, ip: str, **extra):
    """Structured auth logging - NEVER include sensitive data."""
    logger.info(
        event,
        user_id=user_id,
        jti=jti,
        ip=ip,
        **extra
    )

# Usage
log_auth_event(
    "token_refresh",
    user_id=str(user.id),
    jti=token.payload.get("jti"),
    ip=request.META.get("REMOTE_ADDR"),
    tenant_id=str(user.tenant_id),
)
```

---

## Developer Checklist

Before merging any authentication code, verify:

- [ ] Algorithm explicitly defined (RS256, ES256, or PS256)
- [ ] Algorithm whitelist enforced (no dynamic selection from header)
- [ ] `alg: none` explicitly rejected
- [ ] Secrets loaded from environment variables
- [ ] RSA keys >= 2048 bits, HMAC secrets >= 256 bits
- [ ] Claims `iss`, `aud`, `exp` validated on every request
- [ ] `iat` checked against `password_changed_at`
- [ ] Generic 401 errors (no "Signature Mismatch" vs "Expired" distinction)
- [ ] Tokens transmitted only over HTTPS
- [ ] Full tokens NEVER logged (only `jti`, `sub`)
- [ ] Rate limiting enabled on auth endpoints
- [ ] Account lockout after failed attempts
- [ ] CSRF protection if using cookies

---

## Commands

```bash
# Run auth tests
cd backend && pytest tests/auth/ -v

# Run security-specific auth tests
cd backend && pytest -m "auth and security" -v

# Run JWT attack simulation tests
cd backend && pytest tests/security/test_jwt_attacks.py -v

# Check for hardcoded secrets
cd backend && grep -r "SECRET\|PRIVATE_KEY" --include="*.py" | grep -v "env("

# Validate JWT key strength
openssl rsa -in jwt_private.pem -text -noout | grep "Private-Key"
```

---

## Resources

- **Views**: See `apps/auth/views.py` for token endpoints
- **JWT Config**: See `gravitea/settings/base.py` SIMPLE_JWT section
- **Revocation**: See `apps/auth/revocation.py` for blacklist logic
- **Rate Limiting**: See `apps/core/rate_limiter.py` for throttling
- **Tests**: See `tests/auth/` and `tests/security/test_jwt_attacks.py`
- **Reference**: JWT Handbook v0.14.2, RFC 7519, RFC 7518

---

*Last updated: 2026-01-20*
*Security standard: JWT Handbook v0.14.2 compliant*
