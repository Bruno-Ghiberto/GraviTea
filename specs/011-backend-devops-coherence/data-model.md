# Data Model: Backend Coherence & DevOps Master Plan

**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15

This feature does not introduce new Django models or database tables. It modifies infrastructure configuration entities and adds test fixtures. The "entities" below describe the configuration objects being created or modified.

---

## Entity 1: Docker Service Configuration

**Source**: `backend/docker-compose.yml` (merged)

| Service | Profile | Port | Network | Health Check |
|---------|---------|------|---------|--------------|
| postgres | (default) | 5432 | gravitea-shared | `pg_isready` |
| redis | (default) | 6379 | gravitea-shared | `redis-cli ping` |
| web | (default) | 8000→8080 | gravitea-shared | HTTP `/api/v1/health/` |
| postgres-test | test | 5433 | gravitea-shared | `pg_isready` |
| redis-test | test | 6380 | gravitea-shared | `redis-cli ping` |
| web-test | test | 8001→8080 | gravitea-shared | HTTP `/api/v1/health/` |
| jaeger-test | test | 16687 | gravitea-shared | HTTP `:14269` |
| prometheus-test | test | 9091 | gravitea-shared | HTTP `/-/healthy` |
| locust | load | 8089 | gravitea-shared | — |

**Network**: `gravitea-shared` (driver: bridge, name: gravitea-shared — explicit name prevents project prefix)

**State Transitions**:
```text
Profile not active → docker compose --profile test up → Services start → Health checks pass → Ready
Ready → docker compose down → Services stop → Volumes persist
```

---

## Entity 2: Test Settings Module

**Source**: `backend/gravitea/settings/test_postgres.py` (new)

| Field | Type | Default | Source |
|-------|------|---------|--------|
| ENGINE | str | `django.db.backends.postgresql` | Fixed |
| NAME | str | `gravitea_test` | `POSTGRES_TEST_DB` |
| USER | str | `gravitea_test` | `POSTGRES_TEST_USER` |
| PASSWORD | str | `gravitea_test` | `POSTGRES_TEST_PASSWORD` |
| HOST | str | `localhost` | `POSTGRES_TEST_HOST` |
| PORT | str | `5433` | `POSTGRES_TEST_PORT` |
| PASSWORD_HASHERS | list | `[MD5PasswordHasher]` | Fixed (speed) |
| JWT_ALGORITHM | str | `HS256` | Fixed (speed) |

**Relationship**: Inherits from `base.py` (not from `test.py`). Overrides `DATABASES`, `PASSWORD_HASHERS`, JWT settings.

**Validation Rules**:
- Must connect to a running PostgreSQL instance
- Must support RLS policies via session variables
- Must be compatible with `--reuse-db` flag

---

## Entity 3: SQL Initialization Script

**Source**: `database/SQL/` directory (6 files)

| Script | Order | Owns | Idempotent |
|--------|-------|------|------------|
| 000_init_database.sql | 1 | Roles, extensions, permissions, session vars | Required (CREATE IF NOT EXISTS) |
| 001_schema_reference.sql | — | (Deprecated — reference only) | N/A |
| 002_rls_policies.sql | 2 | RLS policies, `get_current_tenant_id()` | Required (CREATE OR REPLACE) |
| 003_stock_functions.sql | 3 | Stock trigger functions | Required (CREATE OR REPLACE) |
| 004_audit_functions.sql | 4 | Audit trigger functions | Required (CREATE OR REPLACE) |
| 005_hardening_constraints.sql | 5 | Extra CHECK constraints | Required (ADD IF NOT EXISTS / DO $$ BLOCK) |

**Execution Order**: Scripts MUST run in numeric order. Bootstrap script enforces this.

**Relationship with Django Migrations**:
- Migrations own: tables, columns, types, indexes, FK constraints
- SQL scripts own: RLS policies, triggers, functions, roles, extensions
- No overlap — hybrid source of truth per research R5

---

## Entity 4: Bootstrap Script

**Source**: `scripts/bootstrap.sh` (new)

| Step | Command | Dependency |
|------|---------|------------|
| 1. Wait for DB | `pg_isready` loop | PostgreSQL container |
| 2. SQL init scripts | `psql -f` (000, 002-005) | Step 1 |
| 3. Django migrations | `python manage.py migrate --noinput` | Step 2 |
| 4. Optional seed | `python manage.py seed_data` | Step 3, `SEED_DATA=true` |
| 5. Start app | `exec "$@"` | Step 4 |

**State Transitions**:
```text
Container start → Wait for DB → SQL scripts → Migrations → [Seed] → App ready
                     ↑ retry loop (2s interval)
```

---

## Entity 5: RLS Test Fixture

**Source**: `backend/tests/conftest.py` (modified)

| Fixture | Scope | Autouse | Purpose |
|---------|-------|---------|---------|
| `set_rls_tenant_context` | function | Yes | Sets `app.current_tenant_id` PostgreSQL session variable |

**Behavior**:
- Runs after `tenant_context` fixture (depends on it)
- Skips for `@pytest.mark.unit` tests (no DB connection)
- Sets session variable before test, resets after test
- Works with both `TestCase` (transaction rollback) and `TransactionTestCase`

**Integration**:
```text
tenant_context fixture (sets Python thread-local)
    → set_rls_tenant_context fixture (sets PostgreSQL session var)
        → test runs (both application-level and DB-level isolation active)
            → cleanup (RESET session var)
```

---

## Entity 6: Cross-Module Integration Test Files

**Source**: `backend/tests/integration/` (new directory)

| File | Modules Tested | Mocking Strategy |
|------|---------------|-----------------|
| test_sale_to_stock.py | ventas → inventario | No mocks (real DB) |
| test_sale_to_invoice.py | ventas → facturacion | Boundary mock (SOAP HTTP only) |
| test_auth_rls_cross_module.py | auth → all modules | No mocks (real RLS) |

**Each test file verifies**:
- Data flows correctly between modules
- Tenant isolation holds across module boundaries
- Transaction rollback cleans up all cross-module state

---

## Entity 7: Analysis Reports

**Source**: `claudedocs/` (new files)

| Report | Spec Reference | Sections |
|--------|---------------|----------|
| 011-cloud-sql-readiness.md | US6, FR-027, SC-007 | Connection strategy, RLS compatibility, backup, migration, performance, security, cost, monitoring, pooling |
| 011-arca-gap-analysis.md | US7, FR-028, SC-008 | Endpoint switching (WSAA/WSFE/CAEA), certificates, response formats, error handling, testing strategy |
