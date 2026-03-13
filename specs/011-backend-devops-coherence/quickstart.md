# Quickstart: Backend Coherence & DevOps Master Plan

**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15

Developer guide for running the full backend stack locally after this feature is implemented.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin) with 4GB+ RAM allocated
- Git
- (Optional) Python 3.14.3 with WSL venv for running tests outside Docker

---

## 1. Clone and Start

```bash
git clone <repository-url>
cd GRAVITEA-ERP/backend

# Copy environment file
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Start the full backend stack (database + cache + web)
docker compose up -d
```

This starts:
- **postgres** (port 5432) — PostgreSQL 18 with RLS policies, triggers, functions
- **redis** (port 6379) — Cache and Celery broker
- **web** (port 8000) — Django backend with auto-reload

The bootstrap script runs automatically on first start:
1. Waits for PostgreSQL readiness
2. Applies SQL init scripts (roles, RLS, triggers, functions)
3. Runs Django migrations
4. Starts the application

**Verify**:
```bash
# Check all services are healthy
docker compose ps

# Hit the health endpoint
curl http://localhost:8000/api/v1/health/
```

Expected response:
```json
{"status": "healthy", "checks": {"database": {"status": "up"}, "cache": {"status": "up"}, "migrations": {"status": "up", "pending": 0}}}
```

---

## 2. Run Tests

### Full Suite (PostgreSQL — default)

Requires the test profile running:

```bash
# Start test database
docker compose --profile test up -d postgres-test redis-test

# Run full test suite (first time — creates DB and applies migrations)
cd backend
venv-wsl/bin/python -m pytest --create-db --tb=short -q

# Subsequent runs (reuses existing DB schema)
venv-wsl/bin/python -m pytest --tb=short -q
```

### Fast Unit Tests (SQLite — no database required)

```bash
cd backend
venv-wsl/bin/python -m pytest -m unit --ds=gravitea.settings.test --tb=short -q
```

### Specific Module Tests

```bash
# Facturacion tests only
venv-wsl/bin/python -m pytest tests/facturacion/ --tb=short -q

# Ventas tests only
venv-wsl/bin/python -m pytest tests/ventas/ --tb=short -q

# Cross-module integration tests
venv-wsl/bin/python -m pytest tests/integration/ --tb=short -q
```

---

## 3. Observability Stack

```bash
# Start observability (after main stack is running)
docker compose -f docker-compose.observability.yml up -d
```

Access monitoring tools:
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger** (traces): http://localhost:16686
- **Alertmanager**: http://localhost:9093

**Verify traces**:
1. Make some API calls: `curl http://localhost:8000/api/v1/health/`
2. Open Jaeger UI → select service `gravitea-backend` → Find Traces

**Verify metrics**:
1. Open Prometheus → query: `django_http_requests_total`
2. Open Grafana → dashboards (pre-configured if available)

---

## 4. Teardown

```bash
# Stop everything (preserves volumes)
docker compose down
docker compose -f docker-compose.observability.yml down

# Full cleanup (removes volumes — fresh start next time)
docker compose down -v
docker compose -f docker-compose.observability.yml down -v
```

---

## 5. Common Operations

### Reset Test Database

```bash
# Force recreation of test DB (after schema changes)
venv-wsl/bin/python -m pytest --create-db tests/ --tb=short -q
```

### Run Load Tests

```bash
docker compose --profile test --profile load up -d
# Locust UI: http://localhost:8089
```

### Seed Data

```bash
docker compose exec web python manage.py seed_ventas
docker compose exec web python manage.py seed_data  # if available
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web

# Structured JSON logs (if LOG_FORMAT=json)
docker compose logs web | python -m json.tool
```

---

## Environment Variables

Key variables in `.env` (see `.env.example` for full list):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SETTINGS_MODULE` | `gravitea.settings.development` | Active settings |
| `DATABASE_URL` | `postgres://gravitea:gravitea@localhost:5432/gravitea` | Main DB connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache connection |
| `SECRET_KEY` | (dev default) | Django secret key |
| `OTEL_TRACING_ENABLED` | `true` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://gravitea-jaeger:4317` | Jaeger OTLP endpoint |
| `LOG_FORMAT` | `json` | Log format (json/text) |
| `ENCRYPTION_KEY` | (dev default) | AES-256-GCM key |
| `HMAC_KEY` | (dev default) | Blind index HMAC key |

---

## Profiles Reference

| Command | What Starts |
|---------|-------------|
| `docker compose up -d` | postgres, redis, web (development) |
| `docker compose --profile test up -d` | + postgres-test, redis-test, web-test, jaeger-test, prometheus-test |
| `docker compose --profile test --profile load up -d` | + locust |
| `docker compose -f docker-compose.observability.yml up -d` | prometheus, grafana, jaeger, loki, promtail, alertmanager |
