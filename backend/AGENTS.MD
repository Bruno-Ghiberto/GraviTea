# GRAVITEA Backend - AI Agent Ruleset

> **Skills Reference**: For detailed patterns, use these skills:
> - [`gravitea-auth`](../skills/gravitea-auth/SKILL.md) - JWT authentication, rate limiting, token lifecycle
> - [`gravitea-tenant`](../skills/gravitea-tenant/SKILL.md) - Multi-tenant isolation, RLS, IDOR prevention
> - [`gravitea-testing`](../skills/gravitea-testing/SKILL.md) - Pytest patterns, fixtures, markers
> - [`gravitea-observability`](../skills/gravitea-observability/SKILL.md) - Prometheus metrics, tracing
> - [`django-expert`](../skills/django-expert/SKILL.md) - Django 5.2 enterprise patterns

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| Creating/modifying models | `gravitea-tenant` + `django-expert` |
| Creating/modifying views, viewsets | `django-expert` |
| Working with JWT tokens, login/logout | `gravitea-auth` |
| Adding rate limiting | `gravitea-auth` |
| Writing tests | `gravitea-testing` |
| Adding Prometheus metrics | `gravitea-observability` |
| Adding OpenTelemetry tracing | `gravitea-observability` |
| Implementing tenant isolation | `gravitea-tenant` |
| Foreign key to tenant-bound model | `gravitea-tenant` |

---

## CRITICAL RULES - NON-NEGOTIABLE

### Models

- ALWAYS: UUIDv7 PKs via `models.UUIDField(primary_key=True, default=uuid.uuid4)`
- ALWAYS: Inherit from `TenantBoundModel` for tenant-scoped data
- ALWAYS: `created_at`/`updated_at` timestamps on all models
- ALWAYS: `DECIMAL(17,3)` for monetary values (never `FLOAT`)
- NEVER: Auto-increment integer PKs for business entities
- NEVER: Models without tenant isolation for tenant data

### Managers

- ALWAYS: Use `TenantBoundManager` for tenant-scoped queries
- ALWAYS: Managers return `.none()` when no tenant context (fail closed)
- NEVER: Use `all_objects` without explicit justification
- NEVER: Raw SQL without RLS context set

### Views

- ALWAYS: Inherit from DRF `ModelViewSet` or `APIView`
- ALWAYS: Define `permission_classes` explicitly
- ALWAYS: Validate tenant ownership in `get_object()`
- NEVER: Business logic in views (use services)
- NEVER: Trust client-provided tenant_id

### Authentication

- ALWAYS: RS256 algorithm for JWT signing
- ALWAYS: Validate `iss`, `aud`, `exp` claims
- ALWAYS: Short-lived access tokens (15-30 min)
- ALWAYS: Refresh tokens stored in Redis with TTL
- NEVER: Log full JWT tokens (only `jti` or `sub`)
- NEVER: Accept `alg: none` or symmetric algorithms from client

### Security (Defense in Depth)

- ALWAYS: Layer 1 (Application) + Layer 2 (RLS) + Layer 3 (Validation)
- ALWAYS: Generic error messages ("Not found") for IDOR attempts
- ALWAYS: Log security events (failed auth, IDOR attempts)
- NEVER: Leak tenant info in error responses
- NEVER: Query across tenants without explicit system context

---

## DECISION TREES

### Model Creation

```
New model needed?
|-- Contains tenant-specific data?
|   |-- Yes -> Inherit TenantBoundModel
|   |   |-- Branch-specific? -> Inherit BranchBoundModel
|   |   +-- Tenant-wide? -> TenantBoundModel
|   +-- No -> Standard Model (system tables only)
|
|-- Has monetary values?
|   |-- Yes -> Use DECIMAL(17,3), never FLOAT
|   +-- No -> Use appropriate field type
```

### Serializer Selection

```
Read operation -> <Model>Serializer
Create operation -> <Model>CreateSerializer
Update operation -> <Model>UpdateSerializer
Nested read -> <Model>DetailSerializer
Has FK to tenant model -> Add IDOR validation
```

### Query Pattern

```
Querying tenant data?
|-- Using TenantBoundManager?
|   |-- Yes -> Safe (auto-filtered)
|   +-- No -> DANGER: Add explicit .filter(tenant=tenant)
|
|-- Need all tenants' data?
|   |-- Admin/system context?
|   |   |-- Yes -> Use Model.all_objects with justification
|   |   +-- No -> FORBIDDEN
```

---

## TECH STACK

| Component | Version |
|-----------|---------|
| Python | 3.14.3 |
| Django | 5.2.x |
| DRF | 3.15+ |
| PostgreSQL | 18.1 |
| Redis | 7.x |
| pytest | Latest |
| prometheus-client | Latest |
| opentelemetry-sdk | Latest |

---

## PROJECT STRUCTURE

```
backend/
├── gravitea/               # Django project settings
│   └── settings/           # base, dev, test, prod
├── apps/
│   ├── core/               # Shared infrastructure
│   │   ├── models/         # Tenant, Branch, base models
│   │   ├── encryption/     # AES-256-GCM utilities
│   │   ├── observability/  # Prometheus, tracing
│   │   └── rate_limiter.py
│   ├── auth/               # JWT authentication
│   │   ├── views.py        # Token endpoints
│   │   ├── jwt.py          # Custom serializer
│   │   └── permissions.py
│   ├── inventario/         # Inventory management
│   │   ├── models.py       # Product, StockMovement
│   │   ├── views.py        # ViewSets
│   │   └── serializers.py
│   └── sync/               # Offline-first sync
│       ├── models.py       # SyncSession, PendingOperation
│       └── views.py        # Push/Pull endpoints
├── tests/                  # Pytest test suite
│   ├── auth/               # Auth-specific tests
│   ├── security/           # OWASP, tenant isolation
│   ├── integration/        # Cross-module tests
│   └── conftest.py         # Root fixtures
└── scripts/                # Utility scripts
```

---

## COMMANDS

```bash
# Development
cd backend && python manage.py runserver
cd backend && python manage.py shell_plus

# Database
cd backend && python manage.py makemigrations
cd backend && python manage.py migrate

# Testing
cd backend && pytest                           # All tests
cd backend && pytest tests/auth/ -v            # Auth tests only
cd backend && pytest -m "security" -v          # Security tests
cd backend && pytest --cov=apps --cov-report=term-missing

# Observability Stack
cd backend && docker-compose -f docker-compose.observability.yml up -d
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686

# Code Quality
cd backend && ruff check apps/
cd backend && mypy apps/
```

---

## NAMING CONVENTIONS

| Entity | Pattern | Example |
|--------|---------|---------|
| Model | `PascalCase` | `StockMovement` |
| Serializer (read) | `<Model>Serializer` | `ProductSerializer` |
| Serializer (create) | `<Model>CreateSerializer` | `ProductCreateSerializer` |
| Serializer (update) | `<Model>UpdateSerializer` | `ProductUpdateSerializer` |
| ViewSet | `<Model>ViewSet` | `ProductViewSet` |
| Service | `<domain>_service.py` | `inventory_service.py` |
| Test file | `test_<module>.py` | `test_tenant_isolation.py` |
| Test class | `Test<Feature>` | `TestTenantIsolation` |
| Fixture | `snake_case` | `authenticated_client` |

---

## API CONVENTIONS

### Response Format

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Product Name",
  "price": "199.990",
  "created_at": "2026-01-20T15:30:00Z"
}
```

### Pagination (Cursor-based)

```json
{
  "next": "http://api/v1/products/?cursor=abc123",
  "previous": null,
  "results": [...]
}
```

### Error Response

```json
{
  "detail": "Not found.",
  "code": "not_found"
}
```

---

## QA CHECKLIST

Before submitting code, verify:

- [ ] `pytest` passes (target: 80% coverage)
- [ ] `ruff check` passes
- [ ] `mypy` passes (if applicable)
- [ ] Migrations created if models changed
- [ ] New endpoints have permission classes
- [ ] Tenant isolation verified (TenantBoundManager used)
- [ ] IDOR validation on all ForeignKeys
- [ ] Security events logged for auth failures
- [ ] No secrets in code (use environment variables)
- [ ] Error messages don't leak tenant info

---

## RELATED DOCUMENTS

- **Data Model**: See `Docs/Project Blueprint/Data Model & Domain Model.md`
- **LLD**: See `Docs/Project Blueprint/Low-Level Design (LLD).md`
- **API Design**: See `Docs/Project Blueprint/REST API Design.md`
- **OpenAPI Specs**: See `api/openapi/` directory

---

*Last updated: 2026-01-20*
*Test Coverage: 79.82% (1471 tests passing)*
