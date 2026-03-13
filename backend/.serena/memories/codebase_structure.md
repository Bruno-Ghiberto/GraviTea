# Gravitea ERP - Codebase Structure

## Directory Layout

```
backend/
├── apps/                           # Django applications
│   ├── auth/                       # Authentication & authorization
│   │   ├── models.py              # AppUser, Role models
│   │   ├── views.py               # Auth endpoints
│   │   ├── jwt.py                 # Custom JWT serializer
│   │   └── serializers.py
│   │
│   ├── core/                       # Shared utilities & infrastructure
│   │   ├── encryption/            # AES-256 field encryption
│   │   │   ├── fields.py          # EncryptedCharField, BlindIndexField
│   │   │   └── utils.py           # Encryption utilities
│   │   ├── exceptions/            # RFC 7807 error handling
│   │   │   └── handlers.py        # problem_detail_exception_handler
│   │   ├── health/                # Health check endpoints
│   │   ├── logging/               # Log filters (trace correlation)
│   │   ├── managers/              # Custom QuerySet managers
│   │   │   └── tenant_bound.py    # TenantBoundManager
│   │   ├── middleware/            # Request middleware
│   │   │   ├── tenant_context.py  # Tenant context injection
│   │   │   └── trace_middleware.py # Trace ID propagation
│   │   ├── models/                # Core models
│   │   │   ├── tenant.py          # Tenant (root entity)
│   │   │   ├── branch.py          # Branch (location)
│   │   │   └── mixins.py          # TenantBoundModel mixin
│   │   ├── observability/         # Metrics, tracing, logging
│   │   │   ├── metrics.py         # Prometheus metrics
│   │   │   ├── tracing.py         # OpenTelemetry setup
│   │   │   └── logging.py         # JSON formatter, sensitive filter
│   │   ├── security/              # Security utilities
│   │   ├── authentication.py      # TenantAwareJWTAuthentication
│   │   ├── fields.py              # MoneyField, PostgresEnumField
│   │   ├── pagination.py          # StandardCursorPagination
│   │   ├── validators.py          # Reusable validators
│   │   └── openapi.py             # Schema postprocessing
│   │
│   ├── inventario/                 # Inventory management
│   │   ├── models.py              # Product, StockMovement, Category, Supplier
│   │   ├── views.py               # Inventory API ViewSets
│   │   ├── serializers.py
│   │   └── services/              # Business logic layer
│   │
│   └── sync/                       # Data synchronization
│       ├── models.py              # Sync queue, conflict resolution
│       ├── views.py               # Sync API endpoints
│       └── services/              # Sync business logic
│
├── gravitea/                       # Django project settings
│   ├── settings/
│   │   ├── base.py                # Common settings
│   │   ├── development.py         # Dev overrides
│   │   ├── production.py          # Production settings
│   │   └── test.py                # Test settings
│   ├── urls.py                    # URL routing
│   ├── celery.py                  # Celery configuration
│   ├── wsgi.py                    # WSGI application
│   └── asgi.py                    # ASGI application
│
├── tests/                          # Test suite (72 test files, 1370+ tests)
│   ├── conftest.py                # Shared fixtures
│   ├── factories.py               # Factory Boy factories
│   ├── auth/                      # Auth tests
│   ├── core/                      # Core utility tests
│   ├── inventario/                # Inventory tests
│   ├── sync/                      # Sync tests
│   ├── unit/                      # Unit tests (fast)
│   ├── integration/               # Integration tests
│   ├── security/                  # Security tests (JWT, encryption, isolation)
│   ├── performance/               # Performance & N+1 tests
│   ├── property/                  # Hypothesis property-based tests
│   ├── docker/                    # Docker integration tests
│   ├── load/                      # Locust load tests
│   ├── fuzz/                      # Schemathesis API fuzzing
│   ├── smoke/                     # E2E smoke tests
│   └── traceability/              # Requirement coverage tests
│
├── requirements/                   # Python dependencies
│   ├── base.txt                   # Core dependencies
│   ├── development.txt            # Dev/test dependencies
│   └── production.txt             # Production extras
│
├── scripts/                        # Utility scripts
├── Docs/                          # Documentation
├── claudedocs/                    # Claude-generated reports
├── observability/                 # Observability configs
│
├── docker-compose.yml             # Core services
├── docker-compose.test.yml        # Test environment
├── docker-compose.observability.yml # Monitoring stack
├── Dockerfile                     # Web container
├── pytest.ini                     # Pytest configuration
├── manage.py                      # Django management
└── .env.example                   # Environment template
```

## Key Models

### Core Domain
- **Tenant** - Customer organization (root entity)
- **Branch** - Physical location within tenant
- **AppUser** - User accounts with tenant/branch assignment
- **Role** - Permission sets for users

### Inventory Domain
- **ProductCategory** - Hierarchical categories
- **Supplier** - Product suppliers (encrypted contact info)
- **PriceList** - Named price lists
- **Product** - Product catalog with encrypted fields
- **ProductPriceHistory** - Price change audit trail
- **ProductCostHistory** - Cost change audit trail
- **StockMovement** - Immutable stock transactions
- **StockSnapshot** - Materialized stock levels
- **BranchStock** - Stock by location

### Sync Domain
- Sync queue models for offline-first operations
- Conflict resolution tracking

## Important Files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared test fixtures (tenant, branch, user) |
| `apps/core/managers/tenant_bound.py` | Automatic tenant filtering |
| `apps/core/models/mixins.py` | TenantBoundModel base class |
| `apps/core/authentication.py` | JWT with tenant context |
| `gravitea/settings/base.py` | Core Django configuration |
| `pytest.ini` | Test markers and coverage config |
