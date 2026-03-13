# Deployment & Infrastructure Guide - Gravitea ERP

## 1. Document Metadata

| Field | Value |
| --- | --- |
| **Owner** | Tech Lead / DevOps |
| **Version** | 1.1 |
| **Last Updated** | 2026-03-01 |
| **Status** | **Active — Local Dev Operational (incl. Rust Acceleration), Production Planned** |
| **Related** | Low-Level Design (LLD), Development Workflow, Architecture Decision Records (ADR) |

---

## 2. Environment Overview

| Environment | Status | Infrastructure |
|-------------|--------|----------------|
| **Local Development** | ✅ Operational | Docker Compose (root `docker-compose.yml`) |
| **Test (Isolated)** | ✅ Operational | Docker Compose `--profile test` |
| **Observability** | ✅ Operational | Docker Compose `--profile observability` |
| **Staging** | ⏳ Planned | Google Cloud Run + Cloud SQL |
| **Production** | ⏳ Planned | Google Cloud Run + Cloud SQL + Memorystore |

---

## 3. Local Development Environment

### 3.1 Architecture

The local environment replicates the production service topology using Docker Compose. The goal is **Local == Prod** — the same container images and configuration run locally and in production.

```mermaid
graph TD
    subgraph "Developer Machine (Docker Compose)"
        FE["frontend :3000\nNext.js dev server (hot reload)"]
        WEB["web :8000\nDjango DRF (dev server)\n+ Rust wheel (PyO3 0.28)"]
        PG["postgres :5432\nPostgreSQL 18-alpine"]
        RD["redis :6379\nRedis 7-alpine"]
    end

    FE -->|REST API| WEB
    WEB --> PG
    WEB --> RD

    subgraph "Optional: --profile observability"
        PROM["prometheus :9090"]
        GF["grafana :3002"]
        JAEGER["jaeger :16686"]
        LOKI["loki :3100"]
        PT["promtail"]
        AM["alertmanager :9093"]
    end

    WEB -->|/metrics| PROM
    WEB -->|OTLP| JAEGER
    WEB -->|JSON logs| PT
    PT --> LOKI
    PROM --> GF
    LOKI --> GF
    PROM --> AM
```

### 3.2 Service Inventory

| Service | Image | Profile | Host Port | Container Port | Purpose |
|---------|-------|---------|-----------|----------------|---------|
| `postgres` | postgres:18-alpine | default | 5432 | 5432 | Primary PostgreSQL 18 database |
| `redis` | redis:7-alpine | default | 6379 | 6379 | Cache + Celery broker |
| `web` | ./backend (Dockerfile) | default | 8000 | 8080 | Django REST API (dev server) + Rust wheel (188 KB, PyO3 0.28) |
| `frontend` | node:22-alpine | default | 3000 | 3000 | Next.js dev server (hot reload) |
| `frontend-prod` | ./frontend-prototype (Dockerfile) | prod | 3001 | 3000 | Next.js production build |
| `prometheus` | prom/prometheus:v2.47.0 | observability | 9090 | 9090 | Metrics collection |
| `grafana` | grafana/grafana:10.2.0 | observability | 3002 | 3000 | Dashboards |
| `jaeger` | jaegertracing/all-in-one:1.51 | observability | 16686 | 16686 | Distributed tracing (UI + OTLP) |
| `loki` | grafana/loki:2.9.0 | observability | 3100 | 3100 | Log aggregation |
| `promtail` | grafana/promtail:2.9.0 | observability | — | — | Log shipping agent |
| `alertmanager` | prom/alertmanager:v0.26.0 | observability | 9093 | 9093 | Alert routing |
| `postgres-test` | postgres:18-alpine | test | 5433 | 5432 | Isolated test database |
| `redis-test` | redis:7-alpine | test | 6380 | 6379 | Isolated test cache |
| `web-test` | ./backend (Dockerfile) | test | 8001 | 8080 | Isolated test Django instance |
| `jaeger-test` | jaegertracing/all-in-one:1.50 | test | 16687 | 16686 | Test tracing |
| `prometheus-test` | prom/prometheus:v2.47.0 | test | 9091 | 9090 | Test metrics |
| `locust` | locustio/locust:2.20 | load | 8089 | 8089 | Load testing UI |

### 3.3 Docker Compose Profiles

```bash
# Default: backend + frontend
docker compose up

# + production-built frontend
docker compose --profile prod up

# + full observability stack (Prometheus, Grafana, Jaeger, Loki, Alertmanager)
docker compose --profile observability up

# + isolated test environment (separate DB, Redis, Django on different ports)
docker compose --profile test up

# + load testing (requires test profile)
docker compose --profile test --profile load up
```

### 3.4 Named Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Primary database data |
| `redis_data` | Redis persistence |
| `frontend_node_modules` | Node modules (avoids host/container path conflicts) |
| `prometheus_data` | Prometheus metrics storage |
| `grafana_data` | Grafana dashboards and config |
| `loki_data` | Loki log storage |
| `alertmanager_data` | Alertmanager state |
| `postgres_test_data` | Test database data |
| `redis_test_data` | Test Redis persistence |

### 3.5 Quick Start

```bash
# 1. Clone and configure environment
git clone <repo> && cd GRAVITEA-ERP
cp backend/.env.example backend/.env  # Set ENCRYPTION_KEY, HMAC_KEY, SECRET_KEY

# 2. Start core services
docker compose up

# 3. Apply database migrations (first time)
docker compose exec web python manage.py migrate

# 4. Seed demo data
docker compose exec web python manage.py seed_all

# 5. Access services
# Backend API:     http://localhost:8000/api/v1/
# Swagger UI:      http://localhost:8000/api/v1/schema/swagger-ui/
# Frontend:        http://localhost:3000
# Django Admin:    http://localhost:8000/admin/
```

**Demo credentials** (after `seed_all`): `admin@gravitea-demo.com` / `admin123`

**Optional: Local Rust development (without Docker)**:
```bash
# Install Rust toolchain (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Build and install the Rust wheel into the WSL venv
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### 3.6 Seed Commands

```bash
# Full seed (recommended — chains all commands)
docker compose exec web python manage.py seed_all

# Individual module seeds
docker compose exec web python manage.py seed_data        # Core: tenants, users, roles
docker compose exec web python manage.py seed_inventario  # Products, categories, suppliers, stock
docker compose exec web python manage.py seed_ventas      # Customers, sale orders
docker compose exec web python manage.py seed_facturacion # ARCA credentials, puntos de venta, comprobantes
```

**`seed_all` chain**: `seed_data` → `seed_inventario` → `seed_ventas` → `seed_facturacion`

### 3.7 Health Checks

All services have Docker-native health checks. Health check commands:

| Service | Command | Interval |
|---------|---------|---------|
| `postgres` | `pg_isready -U postgres` | 10s |
| `redis` | `redis-cli ping` | 10s |
| `web` | `python -c "urllib.request.urlopen('/health/live')"` | 30s |
| `frontend-prod` | `wget --spider http://127.0.0.1:3000/` | 30s |
| Observability | `wget --spider http://localhost:{port}/-/healthy` | 30s |

Django health endpoints:
- `GET /health/live` — Kubernetes liveness probe (always returns 200 if process is running)
- `GET /health/ready` — Kubernetes readiness probe (checks DB + cache connectivity)
- `GET /api/v1/health/` — Combined health check with component status

### 3.8 Key Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | Yes | `gravitea.settings.development` (local) |
| `DATABASE_URL` | Yes | `postgresql://postgres:postgres@postgres:5432/gravitea` |
| `REDIS_URL` | Yes | `redis://redis:6379/0` |
| `SECRET_KEY` | Yes | Django secret key (generate with `openssl rand -hex 50`) |
| `DEBUG` | Yes | `True` (local only) |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1,0.0.0.0` |
| `CORS_ALLOWED_ORIGINS` | Yes | `http://localhost:3000,http://localhost:3001` |
| `ENCRYPTION_KEY` | Yes | Base64-encoded 32-byte key for AES-256-GCM |
| `HMAC_KEY` | Yes | Base64-encoded 32-byte key for blind indexes |
| `OTEL_TRACING_ENABLED` | No | `true` to enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://jaeger:4317` |
| `LOG_FORMAT` | No | `json` (structured logging) |

### 3.9 Observability Stack (Local)

```bash
# Start with full observability
docker compose --profile observability up

# Access points
# Grafana:       http://localhost:3002 (admin/admin)
# Prometheus:    http://localhost:9090
# Jaeger:        http://localhost:16686
# Alertmanager:  http://localhost:9093
# Loki:          http://localhost:3100 (Grafana data source)
```

**Metric categories**:
- HTTP request latency, status codes, in-flight requests (django-prometheus)
- Database query duration, connection pool stats
- Custom business metrics: `sync_operations_total`, `auth_events_total`, `inventory_movements_total`, `api_request_latency`
- Uptime and health check metrics

**Distributed tracing**: `TraceMiddleware` injects `trace_id` on all requests. Spans available in Jaeger for full request traces.

### 3.10 Test Environment

```bash
# Start isolated test environment
docker compose --profile test up

# Test services run on offset ports (no conflict with dev)
# Test DB:      postgres-test :5433
# Test Redis:   redis-test    :6380
# Test Django:  web-test      :8001

# Run tests using the external runner (recommended for AI agents)
scripts/run-tests-external.sh pytest

# Read test results
cat Docs/Tests/latest.status    # 1 line: PASSED/FAILED + summary
cat Docs/Tests/latest.summary   # ~12 lines: counts, failures

# Or run directly in WSL (using WSL venv)
backend/venv-wsl/bin/python -m pytest tests/ --tb=short -q
```

### 3.11 WSL2 / Windows Notes

This project is developed on Windows using WSL2 (Ubuntu 24.04).

| Context | Approach |
|---------|---------|
| **Human development** | Use Docker Compose (all platforms) |
| **AI agent test execution** | WSL venv `backend/venv-wsl/` (Python 3.14.3, avoids Windows Python crash `0xc0000005`) |
| **Rust toolchain** | Rust 1.93.1 via `rustup`, Maturin 1.12.4 via pip in venv-wsl, PyO3 0.28 |
| **File path** | All paths use `/mnt/c/Users/...` from WSL |
| **CRLF handling** | Docker build and runtime strip `\r` from shell scripts via ENTRYPOINT wrapper |

WSL venv location: `backend/venv-wsl/bin/python` (Python 3.14.3, full parity with Windows venv minus `pywin32`).

**Rust in WSL**: The Rust acceleration layer (9 modules, specs 017-025) is compiled via Maturin in WSL2. After any Rust code change, rebuild with:
```bash
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

---

## 4. Production Target Architecture (Planned)

> **Status**: Architecture is designed and ready for deployment. CI/CD pipeline and GCP infrastructure are planned for post-MVP. The project is currently in a research phase evaluating a pivot to Vertical SaaS targeting specific Argentine industry niches (see ADR-016). Production deployment timeline may be adjusted based on research outcomes.

### 4.1 Google Cloud Platform Target

```mermaid
graph TD
    subgraph "Client Layer"
        WEB_CLIENT["Web Browser\n(Next.js)"]
        ELECTRON["Electron Desktop\n(Planned — Post-MVP)"]
    end

    subgraph "CDN / Edge"
        LB["Cloud Load Balancer\n(HTTPS termination)"]
    end

    subgraph "Application Layer — Cloud Run"
        CR_API["api-core\n(Cloud Run — Django REST)"]
        CR_SYNC["api-sync\n(Cloud Run — Sync endpoints)"]
        CR_AUTH["api-auth\n(Cloud Run — Auth + JWT)"]
        CR_WORKER["jobs-worker\n(Cloud Run Jobs — Celery)"]
        CR_FRONTEND["frontend\n(Cloud Run — Next.js SSR)"]
    end

    subgraph "Data Layer — Google Cloud"
        CSQL["Cloud SQL\nPostgreSQL 18.1\n(private IP)"]
        REDIS["Memorystore\nRedis 7.x\n(private IP)"]
        GCS["Cloud Storage\n(static assets, backups)"]
        SM["Secret Manager\n(keys, certificates)"]
    end

    subgraph "Observability — Google Cloud"
        GCL["Cloud Logging\n(JSON log ingestion)"]
        GCM["Cloud Monitoring\n(Prometheus remote write)"]
        CT["Cloud Trace\n(OpenTelemetry OTLP)"]
    end

    WEB_CLIENT --> LB
    ELECTRON --> LB
    LB --> CR_FRONTEND
    LB --> CR_API
    LB --> CR_AUTH
    LB --> CR_SYNC

    CR_API --> CSQL
    CR_API --> REDIS
    CR_API --> SM
    CR_AUTH --> REDIS
    CR_AUTH --> CSQL
    CR_SYNC --> CSQL
    CR_WORKER --> CSQL
    CR_WORKER --> REDIS

    CR_API --> GCL
    CR_API --> GCM
    CR_API --> CT
```

### 4.2 Service Decomposition Plan

The current single Django monolith is designed for future decomposition into separate Cloud Run services. No code changes are required for the decomposition — only deployment configuration.

| Service | Current State | Production Target |
|---------|--------------|-------------------|
| `api-core` | Part of monolith | Cloud Run (auto-scaling, min-instances=1) |
| `api-auth` | Part of monolith | Cloud Run (dedicated, security-hardened) |
| `api-sync` | Part of monolith | Cloud Run (high-throughput, bulk operations) |
| `jobs-worker` | Celery configured | Cloud Run Jobs / Cloud Tasks |
| `frontend` | Next.js dev server | Cloud Run (SSR) or Cloud Storage (static export) |

### 4.3 GCP Infrastructure Components

| Component | GCP Service | Notes |
|-----------|------------|-------|
| **Backend containers** | Cloud Run | HTTP/2, auto-scaling, pay-per-request |
| **Database** | Cloud SQL (PostgreSQL 18.1) | Private IP, automatic backups, PITR |
| **Cache / Message Broker** | Memorystore (Redis 7.x) | Private IP, HA replica |
| **Secrets** | Secret Manager | `ENCRYPTION_KEY`, `HMAC_KEY`, ARCA certificates |
| **Static assets** | Cloud Storage | CDN-backed via Cloud CDN |
| **Container registry** | Artifact Registry | Docker images per feature |
| **Logs** | Cloud Logging | JSON structured logs from Django |
| **Metrics** | Cloud Monitoring | Prometheus remote write or `django-prometheus` scrape |
| **Traces** | Cloud Trace | OpenTelemetry OTLP export |
| **Alerts** | Cloud Monitoring Alerting | Replaces local Alertmanager |

### 4.4 CI/CD Pipeline (Planned — GitHub Actions)

```mermaid
flowchart LR
    subgraph "Local Dev"
        CODE[Code] --> COMMIT[Commit]
        COMMIT --> PUSH[Push to branch]
    end

    subgraph "Continuous Integration (GitHub Actions)"
        PUSH --> BUILD_LINT["Build + Lint\n(Ruff, Black, mypy)"]
        BUILD_LINT --> RUST_BUILD["Build Rust Wheel\n(Maturin + PyO3 0.28)"]
        RUST_BUILD --> UNIT["Unit Tests\n(pytest ~2,500+ tests)"]
        UNIT --> SEC_SCAN["Security Scan\n(bandit)"]
    end

    subgraph "Continuous Delivery"
        SEC_SCAN -->|Success| BUILD_IMG["Build Docker Image\n(multi-stage: rust-builder + app)"]
        BUILD_IMG --> PUSH_REG["Push to Artifact Registry"]
        PUSH_REG --> DEPLOY_STAGE["Deploy to\nCloud Run Staging"]
        DEPLOY_STAGE --> MIGRATE["Run Migrations\non Cloud SQL Staging"]
    end

    subgraph "Release (Manual Trigger)"
        MIGRATE -->|Approve| DEPLOY_PROD["Deploy to\nCloud Run Production"]
    end
```

**Quality gates** (all must pass before deployment):
1. `ruff check` — zero lint errors
2. `mypy --strict` — zero type errors
3. `pytest` — zero new test failures (currently: ~2,500+ passed, including 131 Rust integration tests)
4. `bandit` — no high-severity security findings

**Current state**: CI/CD pipeline is planned. Local development uses Docker Compose + `scripts/run-tests-external.sh` for quality gates.

### 4.5 Secrets Management (Production)

```mermaid
graph LR
    SM["GCP Secret Manager"]
    CR["Cloud Run Service"]
    CSQL["Cloud SQL"]

    SM -->|"ENCRYPTION_KEY\nHMAC_KEY\nSECRET_KEY\nARCA certs"| CR
    CR -->|"Private IP\nCloud SQL Auth Proxy"| CSQL
```

Secret categories:
| Secret | Type | Notes |
|--------|------|-------|
| `ENCRYPTION_KEY` | AES-256 key | Base64-encoded 32 bytes |
| `HMAC_KEY` | HMAC key | Base64-encoded 32 bytes |
| `SECRET_KEY` | Django secret | Min 50 chars, random |
| `DATABASE_URL` | Connection string | Cloud SQL private IP |
| `REDIS_URL` | Connection string | Memorystore private IP |
| ARCA certificates | PEM files | Per-tenant (also encrypted in DB via `ARCACredential`) |

**Current implementation**: `backend/apps/core/secrets.py` provides GCP Secret Manager integration. In local dev, all secrets are environment variables.

### 4.6 Database Configuration (Production Target)

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Engine** | PostgreSQL 18.1 | Cloud SQL for PostgreSQL |
| **Instance tier** | TBD | Based on load testing |
| **Storage** | TBD | Auto-resize enabled |
| **Backups** | Automatic daily | PITR enabled |
| **PITR retention** | TBD (per agreed SLA) | Log retention window |
| **Connections** | Cloud SQL Auth Proxy | No public IP |
| **Migrations** | Applied at deployment | `python manage.py migrate` in Cloud Run entrypoint |
| **RLS** | Enabled | Bootstrap SQL applies RLS policies post-migrate |

**Migration strategy**: Django migrations are applied atomically on each Cloud Run deployment before traffic is shifted. The `--profile test` environment validates migrations before production deployment.

### 4.7 Backup and Recovery Strategy

```mermaid
flowchart LR
    subgraph "Cloud SQL Backups (Planned)"
        PITR["Point-in-Time Recovery\n(PITR activated)"]
        DAILY["Daily Automatic Backup\n(Cloud SQL managed)"]
        WEEKLY["Weekly Export\n(pg_dump to Cloud Storage)"]
    end

    PITR --> LOG_RETAIN["WAL logs retained\nN days (per SLA)"]
    DAILY --> VERIFY["Backup verification\n+ restore test in Staging"]
    WEEKLY --> ENCRYPT["Encrypted dump\nin Cloud Storage bucket"]
```

- **PITR**: Activated with retention window per agreed SLA. Allows recovery to any point within the retention window.
- **Daily backups**: Cloud SQL automatic snapshots. Tested monthly via restore to staging.
- **Weekly exports**: Encrypted `pg_dump` stored in Cloud Storage. Used for disaster recovery and audit.
- **Local development**: Manual backup via `docker compose exec postgres pg_dump -U postgres gravitea > backup.sql`.

---

## 5. Migration Path: Local to Production

### 5.1 Known Considerations

The following items are known requirements for the local-to-production migration:

| Area | Consideration | Status |
|------|--------------|--------|
| **Database** | Run bootstrap SQL (pre-migrate roles/extensions, post-migrate RLS policies) before first deploy | Documented in `backend/database/sql/` |
| **Secrets** | Migrate env vars from `.env` to GCP Secret Manager | Integration code exists in `backend/apps/core/secrets.py` |
| **ARCA certificates** | Per-tenant cert/key stored encrypted in `ARCACredential` table. Production: test certs must be replaced with real ARCA certs | Manual step per tenant |
| **Static files** | `python manage.py collectstatic` to Cloud Storage bucket | `collectstatic` skips JWT key validation (already handled in `apps/auth/apps.py`) |
| **Rust wheel** | `gravitea_rust` wheel must be built via Maturin in the Docker multi-stage build (rust-builder stage) | Automated in Dockerfile |
| **Email** | `EMAIL_BACKEND` in settings must be changed from console backend to SMTP/SendGrid | Configuration change only |
| **CORS** | `CORS_ALLOWED_ORIGINS` must include production frontend domain | Environment variable |
| **`DEBUG=False`** | Activates production security settings (HSTS, secure cookies, etc.) | Environment variable |
| **RS256 keys** | Production RSA private/public keypair must be generated and stored in Secret Manager | Manual step |
| **Migrations** | 23 migrations must apply cleanly to Cloud SQL instance | Tested in local Docker |

### 5.2 Deployment Checklist (Pre-Production)

The following items must be completed before the first production deployment:

**Infrastructure**:
- [ ] Cloud SQL PostgreSQL 18.1 instance created with private IP
- [ ] Memorystore Redis 7.x instance created with private IP
- [ ] Artifact Registry repository created for Docker images
- [ ] GCP Secret Manager secrets populated
- [ ] Cloud Run services configured (api-core, api-auth, api-sync, jobs-worker, frontend)
- [ ] Load Balancer configured with HTTPS termination and custom domain

**Application**:
- [ ] RS256 key pair generated and stored in Secret Manager
- [ ] `ENCRYPTION_KEY` and `HMAC_KEY` generated and stored in Secret Manager
- [ ] Bootstrap SQL scripts executed on Cloud SQL instance
- [ ] `python manage.py migrate` executed successfully
- [ ] `python manage.py collectstatic` executed (static assets to Cloud Storage)
- [ ] Health check endpoints responding (`/health/live`, `/health/ready`)
- [ ] ARCA production credentials obtained from AFIP/ARCA and configured per tenant

**Rust Acceleration**:
- [ ] Rust wheel (`gravitea_rust`) builds successfully in Docker multi-stage (rust-builder stage)
- [ ] `import gravitea_rust` succeeds in production container
- [ ] All 9 Rust dispatcher modules (`*_engine.py`) fall back gracefully if wheel is missing

**CI/CD**:
- [ ] GitHub Actions workflows configured with GCP service account credentials
- [ ] Docker build pipeline validated (including Rust wheel build step)
- [ ] Staging deployment tested end-to-end
- [ ] Smoke test suite passing on staging

**Observability**:
- [ ] Cloud Logging configured to receive JSON logs from Cloud Run
- [ ] Cloud Monitoring metrics collection active
- [ ] Alerting policies configured (fiscal service failures, auth events, P95 latency)
- [ ] Cloud Trace receiving OTLP spans from Django backend

### 5.3 Items Not Yet Studied (TBD)

The following production considerations require further analysis before implementation:

| Item | Notes |
|------|-------|
| **Cloud Run concurrency settings** | Not yet load-tested; concurrency per instance TBD |
| **Cloud SQL instance tier** | Requires load testing to determine appropriate tier |
| **Celery in Cloud Run** | Cloud Run Jobs vs always-on worker vs Cloud Tasks direct migration TBD |
| **Multi-region deployment** | Not planned for MVP; single region (South America / US) TBD |
| **CDN configuration** | Cloud CDN for static assets and potential API caching TBD |
| **VPC configuration** | Private networking topology for Cloud Run → Cloud SQL → Memorystore TBD |
| **Blue-green vs canary deployments** | Deployment strategy for zero-downtime releases TBD |
| **Database connection pooling** | PgBouncer vs Cloud SQL Auth Proxy connection management TBD |
| **Electron desktop client** | Post-MVP; architecture for offline sync, SQLCipher storage, auto-update TBD |

---

## 6. Configuration Reference

### 6.1 Django Settings Structure

| File | Environment | Notes |
|------|-------------|-------|
| `backend/gravitea/settings/base.py` | All | Shared configuration (~550 lines) |
| `backend/gravitea/settings/development.py` | Local | DEBUG=True, console email, relaxed CORS |
| `backend/gravitea/settings/test.py` | CI/Test | In-memory cache, test DB, mocked Celery |
| `backend/gravitea/settings/production.py` | Production | HSTS, secure cookies, GCP integrations |

### 6.2 Django Application Load Order

```python
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    # ... standard Django apps

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",

    # Project apps (load order matters for migrations)
    "apps.core",
    "apps.core.observability",
    "apps.auth",
    "apps.inventario",
    "apps.sync",
    "apps.facturacion",
    "apps.ventas",
]
```

### 6.3 Middleware Stack (Order Matters)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # static files
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.TenantContextMiddleware",  # MUST be last: extracts tenant_id from JWT
]
```

### 6.4 Database Migrations Summary

| App | Migrations | Key Migrations |
|-----|-----------|----------------|
| `auth` | 3 | Initial AppUser+Role, rate limiting fields, unique constraint fix |
| `core` | 3 | Tenant+Branch, TenantBoundModel infrastructure, customization models |
| `inventario` | 6 | Products, categories, suppliers, stock movements, price history, PostgreSQL ENUM types |
| `ventas` | 3 | Customers, sale orders, order items |
| `facturacion` | 3 | ARCA credentials, comprobantes, CAEA |
| `sync` | 5 | Sync sessions, pending operations, conflict fields, retry logic |
| **Total** | **23** | Applied to local Docker PostgreSQL 18 |

### 6.5 DRF Global Configuration

| Setting | Value |
|---------|-------|
| Default authentication | `TenantAwareJWTAuthentication` |
| Default permission | `IsAuthenticated` |
| Pagination | `StandardCursorPagination` (cursor-based, PAGE_SIZE=100) |
| Filtering | `DjangoFilterBackend` |
| Throttling | anon=100/hour, user=1000/hour |
| Renderers | `JSONRenderer` only |
| Exception handler | `problem_detail_exception_handler` (RFC 9457) |
| Schema generator | drf-spectacular (OpenAPI 3.1.0) |
| Decimal handling | `COERCE_DECIMAL_TO_STRING=True` |

### 6.6 OpenAPI Schema URLs

| URL | Purpose |
|-----|---------|
| `/api/v1/schema/` | OpenAPI 3.1.0 JSON/YAML spec |
| `/api/v1/schema/swagger-ui/` | Interactive Swagger UI |
| `/api/v1/schema/redoc/` | ReDoc documentation |
