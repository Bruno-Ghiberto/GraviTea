# Research: Backend Coherence & DevOps Master Plan

**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15 | **Status**: Complete

All 9 NEEDS CLARIFICATION items resolved through codebase analysis.

---

## R1: Docker Compose Profile Syntax

**Decision**: Merge `docker-compose.yml` and `docker-compose.test.yml` into a single file using profiles: `dev` (default), `test`, `load`.

**Rationale**: The test compose (`docker-compose.test.yml`) duplicates 80% of the main compose. Docker Compose profiles (GA since Compose v2.1) allow service grouping within one file. The `load-testing` profile is already used for Locust in the test compose.

**Profile Design**:
| Profile | Services | Command |
|---------|----------|---------|
| (default) | postgres, redis, web | `docker compose up -d` |
| `test` | postgres-test, redis-test, web-test, jaeger-test, prometheus-test | `docker compose --profile test up -d` |
| `load` | locust (extends test) | `docker compose --profile test --profile load up -d` |

**Alternatives Considered**:
- **Keep 2 files**: Simpler mentally but causes service name collisions and env var drift. Rejected.
- **Docker Compose extends**: Compose `extends` requires external files. Same drift risk. Rejected.
- **Profiles in 3 files**: Over-engineers the solution. Rejected.

**Evidence**: `docker-compose.test.yml:143-144` already uses `profiles: [load-testing]` for Locust.

---

## R2: External Network Creation

**Decision**: Main compose defines `gravitea-shared` as a named bridge network (not external). Observability compose references it as `external: true` with explicit `name: gravitea-shared`.

**Rationale**: Docker Compose auto-prefixes network names with the project name (e.g., `backend_gravitea-shared`). Using `name: gravitea-shared` in the network definition prevents this prefix and makes the network predictable. The main compose owns the network lifecycle; observability compose consumes it.

**Implementation**:
```yaml
# docker-compose.yml
networks:
  gravitea-shared:
    driver: bridge
    name: gravitea-shared  # Explicit name prevents project prefix

# docker-compose.observability.yml
networks:
  gravitea-shared:
    external: true
    name: gravitea-shared
```

**Bootstrap requirement**: Main compose must start before observability compose. The `scripts/bootstrap.sh` enforces this order. No manual `docker network create` needed.

**Alternatives Considered**:
- **Manual `docker network create`**: Current approach (see compose file headers). Fragile — forgotten step causes startup failure. Rejected.
- **Both external**: Requires pre-create script. More moving parts. Rejected.
- **Single compose for everything**: Observability has a different lifecycle (can be stopped/started independently). Rejected.

**Evidence**: `docker-compose.yml:83-87` and `docker-compose.observability.yml:125-129` both currently require the pre-created external network.

---

## R3: PostgreSQL Test Database Strategy

**Decision**: Use pytest-django's `--reuse-db` flag with a dedicated PostgreSQL test database running in the Docker `test` profile. Test settings connect to `postgres-test:5433` (mapped from container 5432).

**Rationale**: `--reuse-db` skips database creation and migration on subsequent runs, saving 10-30 seconds per run. The test database persists between runs (Docker volume). First run (or `--create-db`) applies full migration + SQL scripts. Transaction rollback per test provides isolation.

**Configuration**:
- **First run**: `pytest --create-db` (creates DB, runs migrations, applies SQL scripts)
- **Subsequent runs**: `pytest` (reuses existing DB, transaction rollback per test)
- **Schema change**: `pytest --create-db` (forces recreation)
- **Timeout**: 9 minutes max for full suite (~2123 tests)

**Schema reuse flow**:
1. pytest-django checks if test DB exists
2. If yes and `--reuse-db`: skip CREATE DATABASE and migrations
3. Each test runs in a transaction that rolls back → no cleanup needed
4. SQL scripts (RLS, triggers, functions) persist across runs

**Alternatives Considered**:
- **Docker compose `test` service only**: Requires Docker for all test runs. Too slow for TDD cycle. Rejected.
- **SQLite fallback for unit tests**: Already planned — `test.py` (SQLite) preserved for `@pytest.mark.unit` tests with `--ds=gravitea.settings.test`. PostgreSQL is the new default.
- **tmpfs for test DB**: Performance gain minimal vs `--reuse-db`. Adds Docker complexity. Rejected.

**Evidence**: pytest-django docs confirm `--reuse-db` skips `CREATE DATABASE` and `migrate`. Django's `TransactionTestCase` provides per-test isolation with rollback.

---

## R4: Test Settings Module Path

**Decision**: Create new `backend/gravitea/settings/test_postgres.py` inheriting from `base.py`. Update `pytest.ini` default to `test_postgres`. Preserve `test.py` for unit-only runs.

**Rationale**: Modifying `test.py` with env var switches adds complexity to the simple SQLite path. Two explicit settings files are clearer. The `pytest.ini` default changes to PostgreSQL (the comprehensive path). Developers can override with `--ds=gravitea.settings.test` for fast unit runs.

**Module design**:
```python
# test_postgres.py — inherits from base.py, NOT from test.py
# This ensures no SQLite artifacts leak in
from .base import *  # noqa
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_TEST_DB", "gravitea_test"),
        "USER": os.environ.get("POSTGRES_TEST_USER", "gravitea_test"),
        "PASSWORD": os.environ.get("POSTGRES_TEST_PASSWORD", "gravitea_test"),
        "HOST": os.environ.get("POSTGRES_TEST_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_TEST_PORT", "5433"),
    }
}
# Faster password hashing (same as test.py)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# HS256 JWT for test speed (same as test.py)
# ... (copy JWT config from test.py)
```

**pytest.ini change**: `DJANGO_SETTINGS_MODULE = gravitea.settings.test_postgres`

**Fast unit path**: `pytest -m unit --ds=gravitea.settings.test`

**Alternatives Considered**:
- **Env var switch in `test.py`**: `if os.environ.get("USE_POSTGRES")` — harder to reason about. Which settings are active? Rejected.
- **Override `test.py` entirely**: Breaks all existing developer workflows that expect SQLite speed. Rejected.

**Evidence**: `pytest.ini:2` currently hardcodes `DJANGO_SETTINGS_MODULE = gravitea.settings.test`. Django's `--ds` flag (from pytest-django) allows per-run override.

---

## R5: Schema Drift Resolution Strategy

**Decision**: Hybrid source of truth. Django migrations own **app schema** (tables, columns, types, indexes, constraints). SQL scripts own **database-level features** (RLS policies, triggers, functions, roles, extensions) that Django cannot manage.

**Rationale**: Django's migration system cannot express RLS policies, custom PL/pgSQL functions, or role-based access control. These must live in SQL scripts. However, table definitions should never be duplicated — `001_schema.sql` should be deprecated or converted to a reference document.

**Resolution rules**:
| Aspect | Source of Truth | Action on Drift |
|--------|----------------|-----------------|
| Tables, columns, types | Django migrations | Update SQL scripts to match |
| Indexes | Django migrations | Remove from SQL scripts |
| CHECK constraints | Django migrations | Remove from SQL scripts |
| FK constraints | Django migrations | Remove from SQL scripts |
| RLS policies | SQL scripts (`002_rls_policies.sql`, `facturacion_rls.sql`, `ventas_rls.sql`) | Add Django RunSQL migration wrapping the policy |
| Triggers/functions | SQL scripts (`003_stock_functions.sql`, `004_audit_functions.sql`) | No migration equivalent needed |
| Roles/extensions | SQL scripts (`000_init_database.sql`) | No migration equivalent needed |
| Hardening constraints | SQL scripts (`005_hardening_constraints.sql`) | Move to migrations where possible |

**Migration strategy for `001_schema.sql`**:
- Convert to a **reference document** (rename to `001_schema_reference.sql`)
- Stop executing it in bootstrap — Django migrations create all tables
- Keep as documentation of the intended schema for DBA review

**Alternatives Considered**:
- **SQL scripts as sole source of truth**: Loses Django's migration history, rollback, and dependency tracking. Rejected.
- **Django migrations for everything (including RLS)**: Django can't express `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` natively. RunSQL works but is fragile for complex policies. Keep SQL scripts for RLS. Partial adoption.

**Evidence**: `docker-compose.yml:30-31` already comments out SQL init scripts ("Django migrations manage schema"). `000_init_database.sql:122-138` documents the execution order. 6 SQL scripts exist vs 14 Django migrations across 6 apps.

---

## R6: Bootstrap Script Technology

**Decision**: Bash script (`scripts/bootstrap.sh`) called from Docker entrypoint. Handles: wait-for-db → SQL init scripts (000, 002-005) → Django migrations → optional seed data.

**Rationale**: Bash is the standard for Docker entrypoint scripts. It's simple, portable (already in the slim image via `/bin/sh`), and doesn't require Django to be importable for the initial wait-for-db check. The Dockerfile already has a CMD that could call a wrapper.

**Script design**:
```bash
#!/bin/bash
set -euo pipefail

# 1. Wait for PostgreSQL
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  echo "Waiting for database..."
  sleep 2
done

# 2. Run SQL init scripts (idempotent)
for script in 000_init_database.sql 002_rls_policies.sql 003_stock_functions.sql \
              004_audit_functions.sql 005_hardening_constraints.sql; do
  psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "/app/database/SQL/$script"
done

# 3. Django migrations
python manage.py migrate --noinput

# 4. Optional seed data
if [ "${SEED_DATA:-false}" = "true" ]; then
  python manage.py seed_data
fi

# 5. Start application
exec "$@"
```

**Note**: `001_schema.sql` is excluded — Django migrations create tables (see R5).

**Dockerfile change**: `ENTRYPOINT ["scripts/bootstrap.sh"]` with `CMD ["gunicorn", ...]`.

**Problem**: The slim Python image doesn't include `psql` or `pg_isready`. Options:
- Install `postgresql-client` in the production image (adds ~5MB)
- Use Python for wait-for-db: `python -c "import psycopg; psycopg.connect(...)"` with retry loop
- Use Django management command: `python manage.py dbshell` (requires Django setup)

**Resolution**: Install `postgresql-client` in the production stage. The 5MB cost is acceptable for reliable initialization. The builder stage already has `libpq-dev`.

**Alternatives Considered**:
- **Django management command**: `python manage.py bootstrap` — requires Django settings to be valid before DB exists (chicken-and-egg). Rejected.
- **Docker Compose init container**: Compose doesn't have native init containers. Would need a separate service. Over-engineered. Rejected.
- **Python script**: More complex than bash for simple sequential operations. No benefit. Rejected.

**Evidence**: `Dockerfile:56` currently uses `CMD ["gunicorn", ...]` with no entrypoint. `docker-compose.yml:78` overrides with `python manage.py runserver` for dev.

---

## R7: OTEL Collector vs Direct Export

**Decision**: Direct export to Jaeger via OTLP gRPC. No separate OTEL Collector for local development.

**Rationale**: Jaeger's all-in-one image (used in both compose files) already includes an OTLP collector. Adding a separate OTEL Collector adds another container with no benefit for local development. The `OTEL_EXPORTER_OTLP_ENDPOINT` env var already points to Jaeger's OTLP port (4317).

**Current wiring** (already correct):
```yaml
# docker-compose.yml
OTEL_EXPORTER_OTLP_ENDPOINT=http://gravitea-jaeger:4317

# observability compose
jaeger:
  environment:
    COLLECTOR_OTLP_ENABLED: true
  ports:
    - "4317:4317"  # OTLP gRPC
```

**Missing piece**: The compose file sets `OTEL_EXPORTER_OTLP_ENDPOINT` but `config.py:59` reads `OTEL_TRACING_ENABLED` which defaults to `false`. Need to add `OTEL_TRACING_ENABLED=true` to the compose environment.

**Production recommendation**: Add an OTEL Collector in the Cloud Run sidecar for sampling, batching, and export flexibility. Document in Cloud SQL readiness report.

**Alternatives Considered**:
- **OTEL Collector sidecar**: Correct for production but overkill for local development. Document for Phase 5 report. Rejected for local.
- **Zipkin protocol**: Jaeger supports Zipkin but OTLP is the standard. Rejected.

**Evidence**: `docker-compose.observability.yml:63-78` — Jaeger container has OTLP enabled. `config.py:46-64` — TracingConfig reads from env vars.

---

## R8: Cloud SQL Auth Proxy Configuration

**Decision**: Unix socket via Cloud SQL Auth Proxy sidecar (recommended for Cloud Run). Already implemented in `production.py`.

**Rationale**: Google's official recommendation for Cloud Run → Cloud SQL is the Auth Proxy sidecar with Unix socket connection. This provides automatic IAM authentication, encrypted connections, and no VPC requirement.

**Current implementation** (`production.py:43-65`):
```python
# Cloud Run with Unix socket
DATABASES = {
    "default": {
        "HOST": f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME', '')}",
        "PORT": "5432",
        "CONN_MAX_AGE": 0,  # Cloud Run optimization
        "CONN_HEALTH_CHECKS": True,
    }
}
```

**Status**: Already implemented. Needs validation in Cloud SQL readiness report (Phase 5).

**Alternatives Considered**:
- **Private IP (VPC)**: Requires VPC Connector ($7.30/month). More complex networking. Unix socket is simpler and cheaper. Rejected as default.
- **Public IP + SSL**: Less secure, requires IP whitelisting. Rejected.

**Evidence**: `production.py:19-65` already supports both `DATABASE_URL` (TCP) and Unix socket paths.

---

## R9: RLS Session Variable Mechanism

**Decision**: Dual-layer setup in test fixtures. Application-level `set_current_tenant_id()` (existing) PLUS database-level `SET app.current_tenant_id` via a new pytest fixture that executes raw SQL on the database connection.

**Rationale**: The current `set_current_tenant_id()` only sets a Python thread-local variable used by `TenantBoundManager`. It does NOT set the PostgreSQL session variable needed for RLS policy evaluation. When tests run against PostgreSQL with RLS enabled, the `get_current_tenant_id()` SQL function returns NULL (no session variable set), blocking all queries.

**Implementation**:
```python
# In conftest.py — new fixture for PostgreSQL RLS
@pytest.fixture(autouse=True)
def set_rls_tenant_context(tenant_context, request):
    """Set PostgreSQL session variable for RLS enforcement."""
    if "unit" in [m.name for m in request.node.iter_markers()]:
        return  # Unit tests don't use DB
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SET app.current_tenant_id = %s",
            [str(tenant_context.id)]
        )
    yield
    with connection.cursor() as cursor:
        cursor.execute("RESET app.current_tenant_id")
```

**Integration with existing fixtures**: The `tenant_context` fixture already calls `set_current_tenant_id()`. The new fixture adds the DB-level variable. Both are needed — application-level for `TenantBoundManager` filtering, DB-level for RLS policy evaluation.

**Edge case**: Tests using `@pytest.mark.unit` skip this fixture (no DB connection). Tests using `TransactionTestCase` get a fresh connection per test — the fixture runs in the setup phase before each test.

**Alternatives Considered**:
- **Middleware only**: Middleware sets the session variable on HTTP requests. But direct DB queries in tests bypass middleware. Need fixture. Rejected as sole solution.
- **Custom database backend**: Override `DatabaseWrapper.ensure_connection()` to set the variable. Too invasive, affects all connections. Rejected.
- **Connection init hook**: `connection_created` signal sets the variable. Works but is global — harder to control per-test tenant switching. Rejected.

**Evidence**: `002_rls_policies.sql:19-27` defines `get_current_tenant_id()` which reads `app.current_tenant_id` session variable. `conftest.py:144-148` sets application-level tenant context but not DB session variable.

---

## Additional Research Findings

### Environment Variable Audit

Comparing `docker-compose.yml` env section vs `base.py`/`development.py`:

| Variable | Compose | Settings | Status |
|----------|---------|----------|--------|
| `DJANGO_SETTINGS_MODULE` | `production` | N/A | **MISMATCH**: Dev compose uses production settings |
| `DATABASE_URL` | Set | Parsed in dev/prod | OK |
| `REDIS_URL` | Set | Read in base | OK |
| `SECRET_KEY` | Hardcoded | `os.environ.get()` | OK (dev only) |
| `ENCRYPTION_KEY` | Set | Read in base | OK |
| `HMAC_KEY` | Set | Read in base | OK |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Set | Read in config.py | OK |
| `OTEL_SERVICE_NAME` | Set | Read in config.py | OK |
| `OTEL_TRACING_ENABLED` | **MISSING** | Read in config.py (defaults false) | **GAP** |
| `LOG_FORMAT` | **MISSING** | Read in base.py (defaults "text") | **GAP** |
| `JWT_PRIVATE_KEY` | **MISSING** | Read in base.py | **GAP** (OK for dev HS256) |
| `JWT_PUBLIC_KEY` | **MISSING** | Read in base.py | **GAP** (OK for dev HS256) |
| `CORS_ALLOWED_ORIGINS` | Set | Read in base.py | OK |

**Action items**:
1. Change `DJANGO_SETTINGS_MODULE` in compose from `production` to `development`
2. Add `OTEL_TRACING_ENABLED=true` to compose env
3. Add `LOG_FORMAT=json` to compose env for observability
4. Document JWT keys as optional for dev (HS256 fallback in dev settings)
5. Update `.env.example` with all variables

### RLS Coverage Audit (Preliminary)

| Table | RLS Source | Status |
|-------|-----------|--------|
| role | `002_rls_policies.sql` | Covered |
| app_user | `002_rls_policies.sql` | Covered |
| branch | `002_rls_policies.sql` | Covered |
| product_category | `002_rls_policies.sql` | Covered |
| product | `002_rls_policies.sql` | Covered |
| stock_movement | `002_rls_policies.sql` | Covered |
| stock_snapshot | `002_rls_policies.sql` | Covered |
| sync_session | `002_rls_policies.sql` | Covered |
| pending_operation | `002_rls_policies.sql` | Covered |
| facturacion tables | `facturacion_rls.sql` | Covered |
| ventas tables | `ventas_rls.sql` | Covered |

**Full audit required in Phase 2B** — compare all models inheriting `TenantBoundModel` against RLS policy definitions.
