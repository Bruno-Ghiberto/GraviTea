# Architecture Decision Records (ADR) - Gravitea ERP

## 1. Document Metadata

| Field | Value |
| --- | --- |
| **Owner** | Tech Lead |
| **Version** | 1.1 |
| **Last Updated** | 2026-03-01 |
| **Status** | **Active — 16 ADRs (Features 001-025 + Pivot Research)** |
| **Related** | High-Level Design (HLD), Low-Level Design (LLD), Development Workflow |

### ADR Index

| ADR | Title | Date | Status |
|-----|-------|------|--------|
| [ADR-001](#adr-001-web-first-development--deferred-electron-desktop) | Web-First Development — Deferred Electron Desktop | 2025-12-01 | Accepted |
| [ADR-002](#adr-002-single-django-monolith-over-microservices) | Single Django Monolith over Microservices | 2025-12-01 | Accepted |
| [ADR-003](#adr-003-defense-in-depth-multi-tenant-isolation) | Defense-in-Depth Multi-Tenant Isolation | 2025-12-01 | Accepted |
| [ADR-004](#adr-004-rs256-jwt-with-custom-tenant-claims) | RS256 JWT with Custom Tenant Claims | 2025-12-01 | Accepted |
| [ADR-005](#adr-005-immutable-ledger-for-financial-data) | Immutable Ledger for Financial Data | 2025-12-01 | Accepted |
| [ADR-006](#adr-006-aes-256-gcm-field-level-encryption) | AES-256-GCM Field-Level Encryption | 2025-12-01 | Accepted |
| [ADR-007](#adr-007-argon2-password-hashing) | Argon2 Password Hashing | 2025-12-01 | Accepted |
| [ADR-008](#adr-008-jsonb-tenant-customization-over-eav) | JSONB Tenant Customization over EAV | 2026-02-20 | Accepted |
| [ADR-009](#adr-009-problemjson-error-format-rfc-9457) | Problem+JSON Error Format (RFC 9457) | 2025-12-01 | Accepted |
| [ADR-010](#adr-010-docker-compose-consolidation-with-profiles) | Docker Compose Consolidation with Profiles | 2026-02-19 | Accepted |
| [ADR-011](#adr-011-offline-first-sync-with-server-side-conflict-resolution) | Offline-First Sync with Server-Side Conflict Resolution | 2025-12-01 | Accepted |
| [ADR-012](#adr-012-spec-driven-development-workflow) | Spec-Driven Development Workflow | 2026-01-15 | Accepted |
| [ADR-013](#adr-013-external-test-runner-for-ai-agents) | External Test Runner for AI Agents | 2026-02-17 | Accepted |
| [ADR-014](#adr-014-ai-agent-skills-architecture) | AI Agent Skills Architecture | 2026-01-15 | Accepted |
| [ADR-015](#adr-015-rustpyo3-acceleration-layer) | Rust/PyO3 Acceleration Layer | 2026-02-25 | Accepted |
| [ADR-016](#adr-016-vertical-saas-pivot-research) | Vertical SaaS Pivot Research | 2026-03-01 | Proposed |

---

## ADR-001: Web-First Development — Deferred Electron Desktop

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `012-prototype-frontend` |

### Context

The original product vision specified an Electron desktop application as the primary client interface, targeting field sales staff who operate offline. Early development revealed that building the full offline-first backend sync layer was the primary technical challenge, not the client rendering layer. Running parallel Electron and web implementations would divide effort and delay core feature delivery.

### Decision

Adopt **Next.js (App Router) as the primary client framework** for the first version. The Electron desktop client is deferred to post-MVP. The offline-first architecture (sync module, conflict resolution, SyncSession) is built and exposed as a REST API that any future client (Electron, mobile, web) can consume.

**Stack**: Next.js 16.1.6 (App Router) + TypeScript strict + React 19 + shadcn/ui + TanStack Query v5 + Tailwind CSS 4.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Electron desktop first | Deferred — adds Chromium packaging complexity before core backend is stable |
| React SPA (Vite + React Router) | Viable; Next.js chosen for SSR capability and App Router patterns |
| Native mobile (iOS/Android) | Not considered for v1 |

### Consequences

**Positive**:
- Faster time-to-market for web prototype (46 tasks, single engineer sprint)
- Browser-based security model (JWT in memory, no local file system access)
- SSR and streaming available for future optimization
- Sync API abstraction supports future Electron or mobile clients without backend changes

**Negative**:
- True offline-first operation requires future Electron/PWA investment
- Users need network connectivity for current web client
- PWA service worker approach not yet implemented

**Evidence**: `frontend-prototype/` — 52 TypeScript source files, 7 routes. Electron referenced as "planned" in `Deployment & Infrastructure Guide.md`.

---

## ADR-002: Single Django Monolith over Microservices

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

At project start, the service decomposition strategy needed to be chosen. The team size is small and the domain boundaries (auth, inventory, sales, invoicing, sync) are well-understood but their interaction patterns were not yet validated. Premature decomposition into microservices risks creating chatty network boundaries across tightly-coupled business operations (e.g., a sale order triggering stock movements and invoice creation in the same transaction).

### Decision

Build a **single modular Django monolith** with all modules as Django apps within one Django project. The internal design follows a clean layer separation (Models → Services → Serializers → ViewSets → Permissions) that would allow future decomposition into Cloud Run services without code changes.

**Planned decomposition target** (production):
- `api-core`: Inventory, Customers, Sales, Configuration endpoints
- `api-sync`: Offline synchronization endpoints
- `api-auth`: Authentication, token issuance/rotation
- `jobs-worker`: Celery async workers (Pub/Sub, Cloud Tasks)

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Microservices from day one | Rejected — operational overhead (service discovery, distributed tracing, API gateway) premature for v1 team size |
| Schema-per-module database | Rejected — Django ORM cross-app foreign keys require shared schema |
| Serverless functions per endpoint | Rejected — cold start latency incompatible with real-time invoice generation |

### Consequences

**Positive**:
- Shared database transactions across modules (stock movement + invoice in one atomic operation)
- Single deployment unit, single Docker image
- Django admin available across all models
- Decomposition path preserved via service layer

**Negative**:
- Single process scaling (must scale entire monolith, not individual bottlenecks)
- All modules share same Django process restart
- Future extraction of `api-sync` requires database connection configuration changes

**Evidence**: `INSTALLED_APPS` order in `backend/gravitea/settings/base.py`. Single `web` service in `docker-compose.yml`.

---

## ADR-003: Defense-in-Depth Multi-Tenant Isolation

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

Multi-tenant SaaS systems face the risk of data leakage between tenants, whether through application bugs, ORM mistakes, or direct database queries. A single point of failure in tenant isolation is unacceptable for an ERP handling financial and fiscal data. The system must enforce isolation at multiple independent layers.

### Decision

Implement **Defense-in-Depth tenant isolation** with three independent layers:

```
Layer 1 (ORM): TenantBoundManager — auto-filters all ORM queries by tenant_id
Layer 2 (DB):  PostgreSQL RLS — SET LOCAL app.current_tenant_id, policy per table
Layer 3 (Val): _validate_tenant_references() — IDOR prevention on all FK writes
```

- **Layer 1** (`TenantBoundManager`): All ORM queries automatically scoped to `tenant_id` extracted from request JWT. Inherited by all `TenantBoundModel` subclasses.
- **Layer 2** (PostgreSQL RLS): SQL-level policies enforce `tenant_id = current_setting('app.current_tenant_id')`. Set via `TenantContextMiddleware` using `SET LOCAL`. Covers facturacion and ventas modules.
- **Layer 3** (IDOR validation): `_validate_tenant_references()` verifies all foreign key targets belong to the same tenant before write operations.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Schema-per-tenant | Rejected — Django migration complexity, N×migration time per deployment |
| Database-per-tenant | Rejected — connection pool exhaustion, expensive at scale |
| Single `tenant_id` filter only | Rejected — single point of failure; ORM bug bypasses all isolation |
| Application-level only (no RLS) | Rejected — raw SQL queries and Django admin bypass ORM managers |

### Consequences

**Positive**:
- Application bug cannot leak cross-tenant data if RLS is functioning
- RLS provides defense even against raw SQL injection attempts
- IDOR validation prevents authorization confusion attacks

**Negative**:
- `SET LOCAL` must be called before every DB operation (handled by middleware)
- Test setup requires `set_current_tenant_id()` for direct service calls
- Direct service calls in tests need explicit tenant context (unlike API calls which get it from middleware)

**Evidence**: `backend/apps/core/models/mixins.py` (TenantBoundModel), `backend/apps/core/middleware/tenant_context.py`, `backend/database/sql/facturacion_rls.sql`, `backend/database/sql/ventas_rls.sql`.

---

## ADR-004: RS256 JWT with Custom Tenant Claims

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

The API requires authentication tokens that carry tenant context without requiring a database lookup on every request. The token algorithm must be secure against algorithm confusion attacks (a known vulnerability in JWT implementations). In a multi-service architecture, symmetric algorithms create risk if any service's key is compromised.

### Decision

Use **RS256 (4096-bit RSA asymmetric signing)** with an explicit algorithm whitelist. HS256, HS384, and HS512 are explicitly forbidden.

Custom claims injected at token issuance:
- `tenant_id` — UUID of the user's tenant
- `branch_id` — UUID of the user's default branch
- `role_id` — UUID of the user's role
- `permissions` — list of `module.action` strings (e.g., `inventario.*`, `facturacion.create`)

Token configuration:
- **Access token**: 15–30 min lifetime (short-lived)
- **Refresh token**: stored in Redis with TTL, mandatory rotation on each use (blacklisted after use via `rest_framework_simplejwt.token_blacklist`)
- **Rate limiting**: 3-tier login (5/min → 3/min → 15min lockout after 5 consecutive failures)

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| HS256 (symmetric) | Rejected — shared secret risk; in a multi-service future, any service knowing the secret can forge tokens |
| ES256 (ECDSA) | Viable alternative; RS256 chosen for broader library compatibility |
| Opaque tokens (session IDs) | Rejected — requires database lookup on every request, incompatible with offline-first design |

### Consequences

**Positive**:
- No database lookup for permission checks (claims embedded in token)
- Secure in multi-service scenarios (only auth service holds private key)
- Algorithm confusion attacks prevented by whitelist enforcement

**Negative**:
- Permissions are point-in-time (role changes require token refresh)
- Key rotation requires coordinated private/public key update
- Larger token size than HS256

**Evidence**: `SIMPLE_JWT.ALGORITHM = "RS256"` in `backend/gravitea/settings/base.py:267`. `TenantAwareJWTAuthentication` in `backend/apps/core/authentication.py`. `CustomTokenObtainPairSerializer` in `backend/apps/auth/jwt.py`.

---

## ADR-005: Immutable Ledger for Financial Data

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

Fiscal compliance in Argentina (ARCA/AFIP regulations) requires that electronic invoices, once authorized, cannot be modified or deleted. Stock movements represent financial transactions that must maintain a complete, unalterable audit trail. Allowing updates to historical records creates compliance risk and audit trail gaps.

### Decision

**StockMovement** and **Comprobante** are **append-only immutable ledgers**. No UPDATE or DELETE operations are permitted after creation. Corrections are made via compensating entries (counter-movements or credit notes).

- `StockMovementViewSet`: exposes only GET (list/retrieve) and POST (create). No PUT, PATCH, DELETE.
- `Comprobante`: status `AUTORIZADO` and `OBSERVADO` are terminal states — no further status transitions allowed after ARCA authorization.
- SQL trigger guard in `003_stock_functions.sql` protects against RESERVED movement modifications.

**Lifecycle summary**:
- `StockMovement`: COMMITTED | RESERVED | CANCELLED (CANCELLED is final, not deleted)
- `Comprobante`: DRAFT → AUTORIZADO | OBSERVADO | RECHAZADO (AUTORIZADO/OBSERVADO are terminal)
- `SaleOrder`: DRAFT → CONFIRMED → INVOICED (INVOICED is immutable)

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Soft-update with audit log | Rejected — audit log can be tampered; immutability is the only true compliance approach |
| Hard delete with backup | Rejected — backup recovery cannot prove non-manipulation |
| Separate audit table | Rejected — adds complexity without guaranteeing immutability of primary record |

### Consequences

**Positive**:
- Fiscal compliance with ARCA regulations
- Unalterable audit trail for all stock and invoice operations
- No risk of accidental record deletion via admin or ORM

**Negative**:
- Mistakes require compensating entries (credit notes, counter-movements)
- Database grows monotonically (no cleanup via DELETE)
- RESERVED movements require special handling for cancellation (status update, not delete)

**Evidence**: `StockMovementViewSet` in `backend/apps/inventario/views.py`, `Comprobante` model in `backend/apps/facturacion/models.py`, SQL trigger in `backend/database/sql/003_stock_functions.sql`.

---

## ADR-006: AES-256-GCM Field-Level Encryption

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

The system stores PII (Personally Identifiable Information) including supplier tax IDs, email addresses, and physical addresses. ARCA certificates containing private keys must be stored securely. Regulatory requirements (Argentina's data protection law Ley 25.326) require PII to be protected at rest. Searchability over encrypted fields is a critical requirement (e.g., finding a supplier by tax ID).

### Decision

Use **AES-256-GCM authenticated encryption** for field-level PII protection, combined with **HMAC-SHA256 blind indexes** for encrypted field searchability.

**Custom Django field types**:
- `EncryptedCharField` / `EncryptedTextField`: transparently encrypt on save, decrypt on access
- `BlindIndexField`: stores HMAC-SHA256(plaintext) for equality-based search without decrypting

**Storage format**: `base64(nonce || ciphertext || auth_tag)` — nonce is randomly generated per encryption, auth tag provides authenticated encryption.

**Key management**: `ENCRYPTION_KEY` and `HMAC_KEY` as base64-encoded environment variables. GCP Secret Manager integration (`backend/apps/core/secrets.py`) for production.

**Applied to**:
- `Supplier`: `tax_id_encrypted` + `tax_id_hash`, `email_encrypted`, `address_encrypted`
- `Product`: `barcode_encrypted` + `barcode_hash`
- `ARCACredential`: `private_key_pem` (EncryptedTextField), `certificate_pem` (EncryptedTextField)

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Database-level encryption (TDE) | Rejected — coarser granularity, no per-field control, no searchability |
| Application-level without blind indexes | Rejected — cannot search encrypted fields without full table scan |
| External KMS encryption | Future enhancement — GCP Secret Manager already integrated for key references |

### Consequences

**Positive**:
- PII protected at rest even if database backup is accessed
- Searchable via blind indexes without exposing plaintext
- Authenticated encryption prevents ciphertext tampering

**Negative**:
- Cannot use `LIKE`, range queries, or ordering on encrypted fields
- Key rotation requires re-encrypting all affected rows
- Two environment variables required (`ENCRYPTION_KEY`, `HMAC_KEY`)

**Evidence**: `backend/apps/core/encryption/fields.py`, `backend/apps/core/encryption/utils.py`. Test coverage: `tests/test_encryption.py`.

---

## ADR-007: Argon2 Password Hashing

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

Password storage must resist brute-force attacks even if the database is compromised. Modern password cracking uses GPUs that can compute millions of bcrypt hashes per second. The OWASP Password Storage Cheat Sheet recommends memory-hard algorithms that are difficult to parallelize on GPU hardware.

### Decision

Use **Argon2** (via `argon2-cffi` library) as the primary password hasher, with **PBKDF2** as a migration fallback for legacy passwords.

Django `PASSWORD_HASHERS` configuration:
```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # primary
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # migration fallback
]
```

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| bcrypt | Viable but not memory-hard; Argon2 is OWASP-recommended since 2015 Password Hashing Competition |
| scrypt | Similar memory-hardness; less Django ecosystem support |
| PBKDF2 only | Rejected — not memory-hard, vulnerable to GPU-based cracking |

### Consequences

**Positive**:
- Memory-hard hashing defeats GPU-based brute-force attacks
- OWASP-compliant
- PBKDF2 fallback allows transparent migration of existing hashes on next login

**Negative**:
- Higher memory usage per password verification (by design)
- Requires `argon2-cffi` dependency

**Evidence**: `PASSWORD_HASHERS` in `backend/gravitea/settings/base.py:157`.

---

## ADR-008: JSONB Tenant Customization over EAV

| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `014-tenant-customization` |

### Context

Different tenants (businesses) have different data requirements. A pharmacy needs batch numbers on products; a construction company needs project codes on orders. Hardcoding every possible custom field into the schema is not scalable. A flexible customization system is needed that does not require schema migrations per tenant.

### Decision

Implement the **JSONB + Metadata Table** pattern (Shopify/HubSpot approach):
- Add `custom_data = JSONField(default=dict)` to extensible entities: `Product`, `Supplier`, `Customer`, `SaleOrder`
- `TenantFieldDefinition` model stores the schema (name, field_type, required, default_value, choices) per entity type per tenant
- `CustomFieldsMixin` DRF serializer mixin validates `custom_data` against `TenantFieldDefinition` on every serialization
- `DynamicFields` React component renders form fields dynamically based on definitions fetched from API
- 6 supported field types: `text`, `integer`, `decimal`, `boolean`, `date`, `select`
- `TenantModuleConfig`: per-tenant module enable/disable with JSON settings
- `BusinessTemplate`: system-wide onboarding templates (NOT tenant-bound — available to all tenants)

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Entity-Attribute-Value (EAV) | Rejected — complex queries, poor performance, no type safety |
| Separate table per tenant | Rejected — migration nightmare, N tables per tenant, schema drift |
| Full schema migration per customization | Rejected — operational burden, requires downtime or careful migration management |
| Postgres schemas per tenant (schema + JSONB) | Rejected — migration complexity already assessed in ADR-003 |

### Consequences

**Positive**:
- No schema migrations for tenant customization
- Type-safe validation via `TenantFieldDefinition`
- Searchable via PostgreSQL JSONB operators (when indexed)
- BusinessTemplate enables fast tenant onboarding

**Negative**:
- Cannot use standard DB constraints on custom fields (enforced at application layer)
- JSON queries are less ergonomic than column queries
- `custom_data` not directly filterable by standard DRF FilterBackend

**Evidence**: `TenantFieldDefinition`, `TenantModuleConfig`, `BusinessTemplate` in `backend/apps/core/models/customization.py`. `CustomFieldsMixin` in `backend/apps/core/serializers.py`. `DynamicFields` in `frontend-prototype/src/components/inventario/dynamic-fields.tsx`.

---

## ADR-009: Problem+JSON Error Format (RFC 9457)

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

REST APIs need consistent, machine-readable error responses. DRF's default error format is inconsistent across exception types (validation errors, permission errors, and 500 errors have different shapes). Frontend clients and integration partners need predictable error structures to implement reliable error handling.

### Decision

Use **RFC 7807 / RFC 9457 Problem+JSON** as the standard error response format across all API endpoints.

Standard error shape:
```json
{
  "type": "https://gravitea.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request body contains invalid data.",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

Implementation:
- Custom `problem_detail_exception_handler` in `backend/apps/core/exceptions/handlers.py` replaces DRF's default handler
- drf-spectacular post-processing hooks in `backend/apps/core/openapi.py` enrich OpenAPI schema with RFC 7807 error schemas
- Content-Type: `application/problem+json` on error responses

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| DRF default error format | Rejected — inconsistent shape across error types, not machine-readable standard |
| Custom proprietary format | Rejected — non-standard, requires documentation for every integration partner |
| JSON:API error format | Not chosen — heavier standard, primarily for JSON:API-compliant resources |

### Consequences

**Positive**:
- Consistent error shape across all endpoints
- Industry-standard format (RFC 9457 published August 2023)
- OpenAPI schema includes error response definitions
- Frontend error handling is uniform

**Negative**:
- Content-Type switch on errors (`application/problem+json` vs `application/json`)
- Tests must assert `Content-Type: application/problem+json` on error paths

**Evidence**: `problem_detail_exception_handler` in `backend/apps/core/exceptions/handlers.py`. `backend/apps/core/openapi.py`.

---

## ADR-010: Docker Compose Consolidation with Profiles

| Field | Value |
|-------|-------|
| **Date** | 2026-02-19 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `013-e2e-frontend-testing` |

### Context

The local development environment had grown to multiple Docker Compose files: a root `docker-compose.yml`, a `backend/docker-compose.yml`, and a `backend/docker-compose.observability.yml`. This created maintenance overhead (three files to update for any service change), inconsistent startup procedures, and confusion about which file was authoritative. The frontend service was added separately from the backend compose files.

### Decision

**Consolidate all Docker Compose configuration into a single root `docker-compose.yml`** using Docker Compose profiles to enable optional service groups.

Profile structure:
| Profile | Services |
|---------|---------|
| (default) | postgres, redis, web, frontend |
| `prod` | + frontend-prod (:3001) |
| `observability` | + prometheus, grafana, jaeger, loki, promtail, alertmanager |
| `test` | + postgres-test, redis-test, web-test, jaeger-test, prometheus-test |
| `load` | + locust |

Common commands:
```bash
docker compose up                              # Default: backend + frontend
docker compose --profile observability up      # + full observability stack
docker compose --profile test up               # + isolated test environment
```

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Keep multiple files with `-f` flag | Rejected — maintenance burden, error-prone, teams forget to include files |
| Docker Swarm / Kubernetes | Rejected — too complex for local development |
| Tilt / Skaffold | Not chosen — additional tooling dependency |

### Consequences

**Positive**:
- Single file to update for any service change
- Profiles clearly communicate optional service groups
- `docker compose up` starts the complete development environment
- 9 named volumes properly managed

**Negative**:
- Large single file (~300+ lines) is harder to scan than modular files
- Previous `backend/docker-compose.observability.yml` references in docs need updating

**Evidence**: Root `docker-compose.yml` with 17 service definitions across 5 profiles. Previous files removed (consolidated 2026-02-19).

---

## ADR-011: Offline-First Sync with Server-Side Conflict Resolution

| Field | Value |
|-------|-------|
| **Date** | 2025-12-01 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `001-sal-invo-inve-backend` |

### Context

The target deployment environment includes retail locations and field sales staff who operate in areas with unreliable internet connectivity. The system must allow operations (sales, stock adjustments) to proceed offline and synchronize when connectivity is restored. Conflict resolution strategy must be defined when offline clients push operations that conflict with server state.

### Decision

Implement **vector clock-based conflict detection** with **server-authoritative conflict resolution**. Clients generate UUIDs for all created entities (enabling idempotent push). The server is the final authority on conflict outcome.

**Sync architecture**:
- `SyncSession`: per-device session tracking with `sync_vector` (JSONField) for conflict detection
- `PendingOperation`: queued client operations with `operation_type` (CREATE/UPDATE/DELETE), `entity_type`, `entity_id`, `payload`, retry logic
- `POST /sync/push/`: batch, idempotent push — client UUIDs prevent duplicate processing
- `GET /sync/pull/`: cursor-based pull with entity type filtering
- `GET /sync/status/{device_id}/`: device status including pending/conflict counts

**Conflict outcomes**: `APPLIED` (server accepted) or `CONFLICTED` (server rejected, client must resolve).

**Planned local client** (Electron, post-MVP): encrypted SQLite (`SQLCipher`) with `_queue` tables for offline buffering before upload.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Last-write-wins (LWW) | Rejected — data loss risk when two users edit the same record offline |
| CRDTs (Conflict-free Replicated Data Types) | Rejected — too complex for v1; planned for evaluation post-MVP if LWW conflicts are frequent |
| Operational Transformation (OT) | Rejected — primarily for collaborative text editing, not ERP record operations |
| Pessimistic locking | Rejected — incompatible with offline operation |

### Consequences

**Positive**:
- Offline operations proceed without blocking
- Idempotent push prevents duplicate processing on retry
- Server-authoritative resolution simplifies client conflict UI

**Negative**:
- Conflicted operations require manual client-side resolution
- Vector clock implementation complexity
- Full offline capability requires future Electron client with local SQLite

**Evidence**: `SyncSession`, `PendingOperation` in `backend/apps/sync/models.py`. `SyncPushView`, `SyncPullView` in `backend/apps/sync/views.py`.

---

## ADR-012: Spec-Driven Development Workflow

| Field | Value |
|-------|-------|
| **Date** | 2026-01-15 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `011-backend-devops-coherence` (formalized) |

### Context

Feature development was proceeding without consistent upfront planning artifacts. This led to scope creep during implementation, inconsistent architectural decisions across features, and difficulty for AI coding agents to understand the intended design before writing code. A structured workflow was needed that produces machine-readable specification artifacts before implementation begins.

### Decision

Adopt the **speckit spec-driven development workflow** as the mandatory development process for all features numbered 011 onward.

The workflow follows this sequence:
```
specify → clarify → plan → tasks → analyze → implement
```

**Artifacts produced** (in `specs/NNN-feature-name/`):
- `spec.md`: User stories, functional requirements, edge cases, success criteria
- `plan.md`: Architecture decisions, component design, API contracts
- `tasks.md`: Numbered, dependency-ordered implementation tasks (T001, T002, ...)
- `research.md` / `quickstart.md`: Supplementary context as needed

**Feature branch naming**: `{NNN}-{descriptive-slug}` (e.g., `015-blueprint-docs-overhaul`).

**Definition of Done** requires all speckit tasks marked complete before merge.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Agile without artifacts (ad-hoc sprints) | Rejected — insufficient context for AI agent implementation |
| GitHub Issues only | Rejected — issues lack structured architecture and task dependency information |
| Waterfall with detailed spec | Rejected — too rigid, spec.md is intentionally evolving |
| Architecture Decision Records only (no plan/tasks) | Adopted as complement — ADRs document decisions, speckit drives execution |

### Consequences

**Positive**:
- AI coding agents receive structured context before writing any code
- `analyze` step catches cross-artifact inconsistencies before implementation
- `tasks.md` provides dependency-ordered, atomic implementation units
- Feature branches are numbered and traceable to spec artifacts

**Negative**:
- Upfront planning time per feature (specify → clarify → plan → tasks → analyze takes hours)
- Spec artifacts must be maintained if implementation diverges
- Requires discipline to complete speckit before starting to code

**Evidence**: `specs/` directory with `011-backend-devops-coherence/`, `012-prototype-frontend/`, `013-e2e-frontend-testing/`, `014-tenant-customization/`, `015-blueprint-docs-overhaul/`.

---

## ADR-013: External Test Runner for AI Agents

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `011-backend-devops-coherence` |

### Context

AI coding agents (Claude Code) running the full pytest suite in-band consumed 30,000+ tokens per test run due to verbose pytest output (322+ lines). With ~2,129 test functions, a single full test run could exhaust a significant portion of the AI agent's context window, leaving insufficient tokens for code analysis and fixes. Agents were also reading full log files, compounding the problem.

### Decision

Implement a **detached test runner script** (`scripts/run-tests-external.sh`) that executes pytest in the background and writes results to summary files rather than stdout.

**Output files** (in `Docs/Tests/`):
| File | Content | Size |
|------|---------|------|
| `{name}.status` | 1 line: PASSED/FAILED + summary | ~50 chars |
| `{name}.summary` | ~12 lines: counts, failures | ~400 chars |
| `{name}.log` | Full pytest output (grep-only, never read whole) | varies |

**Usage**:
```bash
scripts/run-tests-external.sh pytest                    # Background
scripts/run-tests-external.sh --visible pytest tests/   # Windows Terminal tab
scripts/run-tests-external.sh --fg pytest -k "test_foo" # Foreground
```

**Policy**: All AI agents MUST use this script. Agents MUST NOT read `.log` files in full — use Grep to extract specific failures.

**Token savings**: 96% reduction (322-line log → 12-line summary).

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| `pytest --tb=short -q` (in-band) | Partial mitigation (~40% reduction); still verbose for 2000+ test runs |
| Task subagent delegation | Viable alternative; agent absorbs verbose output, only summary returns. Used as complementary approach |
| pytest-html report | Human-readable HTML, not token-efficient for AI consumption |

### Consequences

**Positive**:
- 96% token reduction per test run
- Agents can run full suite multiple times without context exhaustion
- Summary file format designed for AI consumption (minimal but informative)

**Negative**:
- Test results not visible in-band — must read summary file after run
- Script adds dependency on bash environment (WSL2 or Linux)
- Windows PowerShell requires Git Bash to run

**Evidence**: `scripts/run-tests-external.sh`. Output directory: `Docs/Tests/`. Referenced in `Development Workflow.md` Section 6.

---

## ADR-014: AI Agent Skills Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-01-15 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | Applied project-wide |

### Context

AI coding agents (Claude Code, GitHub Copilot, Cursor) working on the codebase repeatedly made pattern errors due to lack of domain context. Common mistakes included: using incorrect JWT algorithm constants, forgetting TenantBoundModel inheritance, using wrong ARCA API call patterns, and creating tests without proper fixtures. Agent sessions start fresh without memory of previous sessions. Project-level CLAUDE.md was growing unwieldy as a single file containing all context.

### Decision

Implement an **AI Agent Skills Architecture** using modular `SKILL.md` files with auto-invoke triggers defined in `CLAUDE.md`.

**Structure**:
```
skills/
├── gravitea-auth/SKILL.md       # JWT, rate limiting, token lifecycle
├── gravitea-tenant/SKILL.md     # TenantBoundModel, RLS, IDOR
├── gravitea-invoice/SKILL.md    # ARCA WSAA/WSFEv1, CAE, fiscal QR (1,138 lines)
├── gravitea-testing/SKILL.md    # pytest patterns, fixtures, markers
├── gravitea-inventory/SKILL.md  # Products, stock, immutable ledger
├── gravitea-sync/SKILL.md       # Offline sync, conflict resolution
├── gravitea-observability/SKILL.md # Prometheus, tracing, label sanitization
├── gravitea-encryption/SKILL.md # AES-256-GCM, blind indexes
├── gravitea-docker/SKILL.md     # Docker Compose, health checks
├── django-expert/SKILL.md       # Django 5.2 enterprise patterns
└── skill-creator/SKILL.md       # How to create new skills
```

**Auto-invoke triggers** in `CLAUDE.md`: file pattern → skill mapping (e.g., `apps/facturacion/**` → `gravitea-invoice`).

**Marketplace skills** from agentskills.io in `.agents/skills/` (e.g., `vercel-react-best-practices`).

**Cross-session memory**: Serena memories in `.serena/memories/` (60+ files) complement skills with session outcomes and debugging insights.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Single large CLAUDE.md | Rejected — unwieldy at scale, loaded on every request including irrelevant tasks |
| No persistent context (stateless agents) | Rejected — pattern errors repeat across sessions |
| Inline comments in source code only | Rejected — code comments don't provide enough context for complex domain decisions |
| Separate agent documentation repo | Rejected — out-of-sync risk, skills live alongside the code they document |

### Consequences

**Positive**:
- Domain-specific patterns loaded on-demand (not always in context)
- Skills evolve with codebase (git-tracked, versioned)
- Marketplace skills (agentskills.io) integrate with same mechanism
- Pattern errors reduced significantly across sessions

**Negative**:
- Skills must be updated when implementation patterns change
- Auto-invoke depends on file path matching (can be wrong if files are in unexpected locations)
- Two-source complexity (skills/ + .agents/skills/) requires `setup.sh` to propagate

**Evidence**: `skills/` directory (10 custom skills). `CLAUDE.md` auto-invoke rules table. `.agents/skills/vercel-react-best-practices/` (marketplace skill). Serena memories: `.serena/memories/` (60+ files).

---

## ADR-015: Rust/PyO3 Acceleration Layer

| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Status** | Accepted |
| **Deciders** | Tech Lead |
| **Branch** | `017-rust-bootstrap` through `025-rust-custom-field-validator` |

### Context

Profiling revealed several CPU-bound hot paths in the Django backend: AES-256-GCM encryption/decryption (called on every PII field access), IVA tax computation (every invoice), SSRF URL validation (every outbound request), sync conflict resolution (every push), and Prometheus label sanitization (every HTTP request). Python's GIL prevents true parallelism for CPU-bound work. The team needed a way to accelerate these paths without replacing the Django framework or rewriting business logic.

### Decision

Introduce a **compiled Rust acceleration layer** via **PyO3 0.28** (Python-Rust FFI) built with **Maturin 1.12.4**. Each hot path gets a dedicated Rust module with a Python dispatcher that auto-falls back to the original Python implementation if the Rust module is unavailable.

**Architecture pattern**:
```
Python caller → dispatcher (e.g., crypto_engine.py)
  → if _USE_RUST and gravitea_rust available:
      → Rust function via PyO3
  → else:
      → original Python function + warning log
```

**9 Rust modules delivered** (SPEC-017 through SPEC-025):

| Module | Function | Speedup | GIL |
|--------|----------|---------|-----|
| `lib.rs` | Bootstrap, GraviteaError | N/A | N/A |
| `crypto.rs` | AES-256-GCM, HMAC-SHA256 | 8.7x | Released |
| `compute.rs` | IVA, CUIT, importes, stock | 2.1–4.4x | Released (batch) |
| `export.rs` | CSV, XLSX generation | GIL release | Released |
| `observability.rs` | 24 compiled regex patterns | 2.4x | Not released |
| `security.rs` | SSRF validation (831 lines) | Fail-closed | Not released |
| `sync.rs` | Merge conflict resolution | GIL release (batch) | Conditional |
| `arca.rs` | CAEA batch builder | GIL release | Released |
| `validation.rs` | Custom field validation | <2ms | Not released |

**Docker integration**: Multi-stage `rust-builder` stage compiles the wheel, reducing image size by 68 MB. Maturin produces a 188 KB wheel.

**Test strategy**: Each module has both Rust-side cargo tests and Python-side pytest integration tests. Parity tests verify Rust output matches Python output for identical inputs. Benchmark tests validate speedup claims.

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Cython | Rejected — less portable, harder to test independently, no cargo ecosystem |
| C extension (CPython API) | Rejected — unsafe memory management, no cargo/crate ecosystem |
| Rewrite in Go (separate service) | Rejected — network overhead for every call, deployment complexity |
| Numpy/SIMD for numeric paths | Partial applicability — only helps numeric, not string/regex paths |
| Accept Python performance | Rejected — encryption at 8.7x is a material user-facing improvement |

### Consequences

**Positive**:
- 2-9x speedup on measured hot paths
- Zero-regression deployment: Python fallback if Rust module unavailable
- Rust type safety catches bugs at compile time (e.g., integer overflow, null handling)
- GIL release on batch operations enables true parallelism
- Single wheel artifact (188 KB) — no external Rust runtime dependency

**Negative**:
- Team must maintain two languages (Python + Rust)
- Maturin build step adds ~7s to Docker build (incremental)
- PyO3 FFI boundary has per-call overhead (~0.3-0.5 microseconds) — not beneficial for sub-microsecond operations
- JSON serialization at FFI boundary limits speedup for small payloads

**Evidence**: `rust/gravitea-core/` (Cargo workspace). `backend/apps/core/*/` dispatchers (`crypto_engine.py`, `ssrf_engine.py`, etc.). `backend/tests/rust_integration/` (test suite). `Dockerfile` (rust-builder stage). `specs/017-*` through `specs/025-*`.

---

## ADR-016: Vertical SaaS Pivot Research

| Field | Value |
|-------|-------|
| **Date** | 2026-03-01 |
| **Status** | Proposed |
| **Deciders** | Product Owner, Tech Lead |
| **Branch** | N/A (research phase, no code changes) |

### Context

After implementing features 001-025 (backend, frontend prototype, Rust acceleration, API audit), the team assessed the go-to-market viability of a general-purpose ERP. Key findings:

1. **Scope infinity**: A general ERP competes with SAP Business One, Odoo, Colppy, and Xubio — each with hundreds of developer-years of investment. A team of 4 (2 devs) cannot match breadth.
2. **No differentiation**: The "offline-first + cloud" value proposition is not enough to overcome switching costs for businesses already using established ERPs.
3. **Unsustainable roadmap**: The MVP required modules for Purchases, Reports, Electron POS, GCP deployment, and CI/CD — each a multi-week effort — before any customer could be acquired.

The hypothesis is that a **vertical SaaS** approach (dominating one industry niche) is more viable than a horizontal ERP approach for a small team.

### Decision

**Pause the general-purpose MVP roadmap** and enter a research phase to evaluate pivoting to a vertical SaaS product. The existing codebase (auth, inventory, sales, invoicing, sync, encryption, Rust acceleration, tenant customization) serves as the platform layer that would be adapted to a specific niche.

**Four candidate niches under evaluation**:

| Niche | TAM | ARPU/mo | Codebase Gap | Key Differentiator |
|-------|-----|---------|--------------|-------------------|
| Distribuidoras (beverage/food) | ~20,000 | $200-600 | ~40% new | Offline drivers, envases retornables |
| Ferreterías (hardware stores) | ~70,000+ | $100-300 | ~30% new | Bulk price updates, inflation management |
| Acopiadores (grain collectors) | ~3,000 | $500-2,000 | ~60% new | AFIP Form 1116, regulatory moat |
| Frigoríficos (meat processors) | ~3,000 | $1,000-5,000 | ~50% new | SENASA + AFIP dual compliance |

**Validation plan**:
1. Research prompt deployed to Perplexity/Gemini Deep Research for market data
2. 5-10 customer discovery interviews in top 2 niches
3. Decision expected late March 2026
4. Post-decision: adapt data model, build niche-specific modules, resume development

### Alternatives Considered

| Option | Outcome |
|--------|---------|
| Continue general ERP path | Rejected — unsustainable scope for team size, no competitive moat |
| Build a platform/marketplace | Rejected — requires developer ecosystem, too early |
| Pivot to consulting/services | Rejected — not scalable, not aligned with SaaS vision |
| Abandon project | Rejected — significant codebase investment (25 features, 7,184 symbols) has value as platform |

### Consequences

**Positive**:
- Focused feature set reduces scope to achievable MVP
- Niche-specific features create competitive moat (regulatory compliance, domain workflows)
- Existing codebase (offline-first, ARCA, Rust acceleration, tenant customization) provides platform foundation
- Customer discovery validates demand before further development investment

**Negative**:
- General-purpose MVP paused — May 2026 target abandoned
- Risk of choosing wrong niche (mitigated by research + interviews)
- Some existing features may not be needed for chosen niche (sunk cost)
- Team must acquire domain expertise in the chosen vertical

**Evidence**: `Docs/Brainstorming/niche-erp-argentina-research-prompt.md` (research prompt). `Docs/Brainstorming/Opportunities.md`. Serena memory: `session-2026-03-01-niche-pivot-brainstorm`.

---

## 2. ADR Process

### Creating New ADRs

New ADRs should be created when:
- A significant technical decision is made that affects multiple components
- A decision was made that future team members would otherwise question
- A technology or pattern is adopted project-wide

**Format**: Copy the template from any existing ADR above. Required fields: Date, Status, Context, Decision, Alternatives Considered, Consequences, Evidence.

**Numbering**: Sequential (ADR-015, ADR-016, ...). Update the index table in Section 1.

### ADR Status Values

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet implemented |
| **Accepted** | Decided and implemented |
| **Superseded by ADR-NNN** | Replaced by a newer decision |
| **Deprecated** | No longer relevant (technology removed) |
