# GRAVITEA-ERP Architecture (Updated 2026-02-15)

## Tech Stack
- Django 5.2+ / DRF / PostgreSQL 18 / Redis 7 / Celery
- Multi-tenant: RLS (25+ tables) + TenantBoundModel + JWT tenant claims
- ARCA fiscal: WSAA/WSFE/CAEA — dual env (homo/prod) via `is_production` flag
- Target deployment: Cloud Run + Cloud SQL + Memorystore

## 6 Backend Modules
| Module | Path | Status |
|--------|------|--------|
| AUTH | `backend/apps/auth/` | RS256 JWT (4096-bit), rotation, blacklisting |
| CORE | `backend/apps/core/` | Tenant/Branch, AES-256-GCM encryption, observability, health, middleware |
| FACTURACION | `backend/apps/facturacion/` | ARCA SOAP, encrypted credentials, QR, 4 migrations |
| INVENTARIO | `backend/apps/inventario/` | Products, stock (immutable ledger), Celery tasks, 4 migrations |
| VENTAS | `backend/apps/ventas/` | Customers, SaleOrders, RLS policies, 3 migrations |
| SYNC | `backend/apps/sync/` | Offline-first, pending ops, conflict resolution, 5 migrations |

## Docker Infrastructure
- `backend/docker-compose.yml` — PostgreSQL 18 + Redis 7 + Django web (Gunicorn)
- `backend/docker-compose.observability.yml` — Prometheus/Grafana/Jaeger/Loki/Promtail/Alertmanager
- `backend/docker-compose.test.yml` — test environment with Locust
- `backend/Dockerfile` — multi-stage Python 3.14.3-slim

## Database Layer
- **SQL scripts**: `database/SQL/000-005` (init, schema, RLS, stock funcs, audit, hardening)
- **Migrations**: 14 files across 6 apps (20 total with latest)
- **Seeds**: `database/seeds/{test_data,test_scenarios}.sql` + `seed_data` management command
- **RLS**: `database/SQL/002_rls_policies.sql` + `backend/database/sql/{facturacion,ventas}_rls.sql`

## Settings
- `backend/gravitea/settings/base.py` (545 lines — comprehensive)
- `development.py`: DEBUG, LocMemCache, CORS allow all
- `production.py`: Cloud SQL (Unix socket), Memorystore, HSTS, JSON logging
- `test.py`: SQLite in-memory (KNOWN GAP — RLS/triggers untested)

## Observability
- Code: `backend/apps/core/observability/{config,metrics,tracing,logging,alerts,business_metrics,uptime}.py`
- Health: `backend/apps/core/health/{checks,views,responses,urls}.py`
- Docker configs: `backend/observability/{prometheus,alertmanager,loki,promtail}.yml`

## Specs
- `specs/001-backend-core/` through `specs/010-ventas-integration/` (10 specs)

## CI/CD
- `.github/workflows/{ci,security-tests,load-tests}.yml`
- pytest markers: unit, integration, security, performance, critical, docker, load, fuzz

## Known Issues (2026-02-15)
1. test.py uses SQLite — RLS/triggers/functions never exercised
2. Dual schema definitions (SQL scripts vs migrations) — drift risk
3. `gravitea-shared` network auto-creation unclear
4. Observability Docker wiring needs validation
5. No single-command DB bootstrap script
