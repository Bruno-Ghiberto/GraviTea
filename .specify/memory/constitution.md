# Gravitea ERP Backend Constitution

## Core Principles

### I. Ironclad Data Model
The database is the last line of defense. PostgreSQL 18.1 (Cloud SQL Enterprise Plus) serves as the foundation. Mechanical integrity is enforced at the database level with `ON DELETE RESTRICT` on all foreign keys and strict check constraints (e.g., non-negative prices/quantities). Financial precision uses `DECIMAL(17, 3)` exclusively for storage - `FLOAT`/`DOUBLE` are prohibited. Display precision is 2 decimal places for user-facing values. Critical movements (`stock_movements`, `account_ledger`) follow an append-only ledger pattern where the past is never edited, only corrected through contra-entries.

**Rationale**: Database-level constraints prevent data corruption even when application logic fails. Financial accuracy and audit trails are non-negotiable for ERP systems.

### II. Multi-Tenant Isolation (RLS Hardened)
Tenant isolation is paramount. PostgreSQL Row Level Security (RLS) is mandatory on all transactional tables, making cross-tenant data access physically impossible. The backend establishes three-layer tenant isolation:

1. **Serializer Layer**: Validates tenant_id/branch_id in request data
2. **Model Layer**: `TenantBoundModel._validate_tenant_references()` enforces FK tenant consistency
3. **Database Layer**: PostgreSQL RLS policies provide final enforcement

The backend must establish `tenant_id` and `branch_id` in the authentication layer, injecting them into session context (`app.current_tenant`) at request start. No queries execute without this context - enforced by RLS.

**Rationale**: Multi-tenant security breaches are catastrophic. Three-layer defense provides defense-in-depth that cannot be bypassed by single-point failures.

### III. Modular Django Architecture
The backend follows a monolithic modular pattern using Django Apps:

**Implemented Modules:**
- `core` - Infrastructure module providing `TenantBoundModel`, encryption services, rate limiting, observability foundation (app_label: gravitea_core)
- `auth` - Authentication and authorization system with JWT tokens, roles, users (app_label: gravitea_auth)
- `inventario` - Inventory management for products, stock levels, movements (app_label: gravitea_inventario)
- `sync` - Offline-first synchronization for POS clients (app_label: gravitea_sync)
- `facturacion` - ARCA integration for electronic invoicing (app_label: gravitea_facturacion)
- `ventas` - Sales processing, customer management, invoice integration (app_label: gravitea_ventas)

**Acopio Vertical Modules (spec-03+):**
- `acopio` - Grain reception, quality analysis, merma calculation, storage, CPE integration (app_label: gravitea_acopio)
- `cuentas` - Producer current accounts, grain ledger, price fixation (app_label: gravitea_cuentas)

**Future Modules (Deferred):**
- `compras` - Purchases and supplier management
- `clientes` - Customer relationship management (extended CRM beyond ventas.Customer)
- `reportes` - Business intelligence and reporting

Views/ViewSets remain lightweight (orchestration only). Business invariants reside in Domain Services, complex queries in Repositories/Query Services. Each module maintains clear boundaries and explicit dependencies.

**Rationale**: Modular architecture enables team scalability, independent testing, and future service extraction while avoiding premature microservices complexity.

### IV. Application-Level Encryption (Defense in Depth)
Sensitive data (PII/fiscal) requires application-level encryption using AES-256-GCM via the `cryptography` library with custom wrapper implementation in `apps/core/encryption/`. This applies to both server-side storage and offline POS local storage (Electron client). Master keys are stored in Google Secret Manager, never in code/Docker/Git. Searchable encrypted fields use blind indexing with HMAC-SHA256 deterministic hashes on normalized data. All encryption operations occur in server memory (backend) or secure local storage (offline client).

**Rationale**: Defense in depth protects against database breaches. Regulatory compliance (GDPR/local privacy laws) demands encryption of sensitive data.

### V. Secure Authentication & Sessions
Password hashing uses `Argon2PasswordHasher` (via `argon2-cffi`) to resist GPU/ASIC attacks. Primary authentication mechanism is JWT tokens (not session cookies) via `djangorestframework-simplejwt`. Session cookies still enforce `SESSION_COOKIE_SECURE = True` (HTTPS only) and `SESSION_COOKIE_HTTPONLY = True` (XSS mitigation) for admin interface access.

IDOR/IDR prevention requires three-layer validation:
1. **Serializer validation**: Checks tenant_id/branch_id in request data
2. **Model validation**: `TenantBoundModel._validate_tenant_references()` enforces FK tenant consistency
3. **Database RLS**: PostgreSQL policies provide final enforcement

Production must never run with `DEBUG = True`, and `SECRET_KEY` requires rigorous protection.

**Rationale**: Authentication is the gateway to all system access. Modern threats require state-of-the-art password hashing, token-based authentication, and multi-layer tenant isolation validation.

### VI. Fiscal Compliance Integration (ARCA)
The `facturacion` module implements robust integration with ARCA Web Services (WSAA/WSFEv1) for electronic invoicing (CAE/CAEA). Communication uses SOAP over HTTPS. The system handles the complete WSAA flow: TRA generation, X.509 certificate signing to create CMS, Base64 encoding, and `LoginCMS` invocation for Token/Sign receipt. Fiscal secrets reference Secret Manager, and ARCA responses persist in Comprobante `arca_response` (JSONB).

**Rationale**: Legal compliance is mandatory for Argentine retail operations. Fiscal integration failures can result in business closure.

### VII. Offline-First & Contingency Support
The backend supports offline-first pragmatic architecture. The SYNC module receives offline sales (contingency receipts/remitos) and manages deferred fiscalization (CAE requests) when connectivity restores. Conflict resolution follows documented strategies:

- **Configuration data**: `server_wins` - server values always take precedence
- **Inventory levels**: `last_write_wins` - most recent update prevails, with audit trail
- **Sales transactions**: `additive` - combine transactions from all sources
- **Customer data**: `most_complete_wins` - merge with preference for complete records
- **Document numbering**: `server_assigns_final` - temporary offline numbers replaced by server sequence

**Rationale**: Argentine retail operates with intermittent connectivity. Business continuity requires robust offline support with clear, predictable conflict resolution.

### VIII. Query Optimization
Django QuerySets must extensively use `select_related()` for FK relationships and `prefetch_related()` for M2M/reverse FK to prevent N+1 queries. Database access patterns require continuous monitoring and optimization. Query performance directly impacts system scalability.

**Rationale**: N+1 queries are the most common performance killer in Django applications. Proactive optimization prevents production emergencies.

### IX. Secure Data Operations
ModelForms explicitly list allowed `fields` to prevent mass assignment vulnerabilities - `fields = '__all__'` is forbidden in production. Bulk operations use `bulk_create()` and `bulk_update()` for performance, acknowledging that signals and custom `save()` methods are bypassed. All data mutations require explicit permission checks.

**Rationale**: Mass assignment vulnerabilities enable privilege escalation. Explicit field listing provides defense against malicious input.

### X. Test-Driven Development
Automated testing is fundamental. Separate TestClass for each model/view using `django.test.TestCase` or transactional variants. Tests must be written before implementation (TDD approach). Code coverage targets: 80% minimum, 95% for critical paths (payments, inventory, fiscal).

**Rationale**: ERP systems handle business-critical operations. Comprehensive testing prevents costly production failures.

### XI. JWT Authentication
Token-based authentication provides stateless, scalable authentication via `djangorestframework-simplejwt`. Custom JWT claims include:

- `tenant_id`: Current tenant context
- `branch_id`: Current branch context
- `email`: User email for audit trails
- `full_name`: Display name for UX

Token lifetimes:
- **Access Token**: 15 minutes (security-first approach)
- **Refresh Token**: 7 days (balance security/UX)

Token blacklisting activates on logout to prevent replay attacks. Rate limiting applies to login endpoint with progressive lockout (see Section XII).

**Rationale**: JWT tokens enable horizontal scaling without shared session state. Short-lived access tokens limit exposure window for compromised tokens. Blacklisting prevents unauthorized access from stolen refresh tokens.

### XII. Rate Limiting Strategy
Progressive lockout protects authentication endpoints from brute force attacks:

- **5 failures**: 5-minute lockout
- **10 failures**: 30-minute lockout
- **20 failures**: Account lock requiring manual intervention

Implementation uses cache-based storage (Redis in production, LocMem in development). Tracking combines IP address + email to mitigate distributed attacks. Automatic reset occurs on successful authentication to prevent legitimate user lockout from typos.

**Rationale**: Authentication endpoints are primary attack vectors. Progressive lockout balances security (prevents brute force) with usability (typos don't permanently lock accounts).

### XIII. Cursor-Based Pagination
All list endpoints use cursor-based pagination for consistent performance at scale:

- **Default page size**: 100 items
- **Maximum page size**: 1000 items
- **Ordering**: `created_at` descending (newest first)

Cursor pagination prevents offset-based performance degradation on large datasets. Ordering by `created_at` provides stable pagination regardless of inserts/deletes during pagination.

**Rationale**: Offset-based pagination degrades linearly with dataset size and becomes unstable with concurrent modifications. Cursor pagination maintains O(1) performance and consistency.

### XIV. API Documentation
OpenAPI 3.0 schema generation via `drf-spectacular` provides machine-readable API documentation:

- **Swagger UI**: `/api/v1/schema/swagger-ui/` - Interactive API explorer
- **ReDoc**: `/api/v1/schema/redoc/` - Clean documentation UI
- **Schema Export**: `/api/v1/schema/` - Raw OpenAPI JSON/YAML

Documentation auto-generates from serializers, viewsets, and docstrings. All endpoints require explicit schema annotation for consistent documentation quality.

**Rationale**: API documentation is critical for frontend development, integration partners, and long-term maintainability. Auto-generation from code ensures documentation never drifts from implementation.

## Technology Stack

### Core Framework
- **Language**: Python 3.14.3
- **Framework**: Django 5.2.x (latest stable)
- **API Layer**: Django REST Framework (latest stable)
- **Database**: PostgreSQL 18.1 (Cloud SQL Enterprise Plus)

### Security & Encryption
- **Password Hashing**: Argon2 via `argon2-cffi`
- **Encryption**: AES-256-GCM via `cryptography` library with custom wrapper in `apps/core/encryption/`
- **Authentication**: JWT tokens via `djangorestframework-simplejwt`
- **Key Management**: Google Secret Manager
- **Session Security**: HTTPS-only cookies with HTTPOnly flag (admin interface)

### Infrastructure
- **Cloud Provider**: Google Cloud Platform
- **Database Service**: Cloud SQL Enterprise Plus
- **Container Runtime**: Docker
- **Orchestration**: Kubernetes (GKE)

## Development Workflow

### Code Review Requirements
1. All code requires peer review before merge
2. Database migrations require DBA approval
3. Security-related changes require security team review
4. Fiscal module changes require compliance verification

### Testing Gates
1. Unit tests must pass (100% success rate)
2. Integration tests for API endpoints
3. Performance tests for new queries
4. Security scan for dependencies

### Deployment Process
1. Feature branches merge to `develop`
2. `develop` deploys to staging after tests pass
3. Production deployments from `main` branch only
4. Rollback plan required for database migrations

## Governance

The constitution supersedes all other development practices. Amendments require:

1. **Documentation**: Clear rationale and impact analysis
2. **Approval**: Technical lead and security team sign-off
3. **Migration Plan**: Step-by-step transition for existing code
4. **Version Bump**: Following semantic versioning rules

All pull requests must verify constitutional compliance. Violations block merge. Complexity additions require explicit justification against constitution principles.

Use `.specify/agent-file.md` for runtime development guidance and context.
