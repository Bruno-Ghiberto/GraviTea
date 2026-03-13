# GRAVITEA-ERP Frontend Prototype

Developer-facing prototype frontend for exercising all 62 backend API endpoints. Built as an internal testing and validation tool — not a production UI.

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js (App Router) | 16.1.6 |
| Language | TypeScript (strict mode) | 5.x |
| UI Library | React | 19.2.3 |
| Components | shadcn/ui (Radix + Tailwind) | latest |
| Data Fetching | TanStack Query | v5 |
| Styling | Tailwind CSS | 4.x |
| Auth | JWT in React state (memory only) | - |
| Output | Standalone (Docker-ready) | - |

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Docker | 29+ | **Required** — runs the full stack |
| Docker Compose | v2+ | Included with Docker Desktop |
| Node.js | 20+ LTS | Only needed for local (non-Docker) development |

## Quick Start (Docker — Recommended)

**One command starts everything**: PostgreSQL, Redis, Django backend, and Next.js frontend.

```bash
# From the repository root (NOT from frontend-prototype/)
cd /path/to/GRAVITEA-ERP

# Start the full stack
docker compose up -d
```

This starts:

| Service | URL | Description |
|---------|-----|-------------|
| `postgres` | localhost:5432 | PostgreSQL 18 database |
| `redis` | localhost:6379 | Redis 7 cache |
| `web` | http://localhost:8000 | Django backend API |
| `frontend` | http://localhost:3000 | Next.js production build |

### First-Time Setup

On the first run, the backend automatically:
1. Waits for PostgreSQL to be ready
2. Runs database migrations
3. Applies RLS policies and database functions

You still need to create a user to log in:

```bash
# Create a superuser (one-time)
docker compose exec web python manage.py createsuperuser
# Enter: email, password (remember these for the frontend login)
```

To seed ALL test data (recommended):

```bash
# Single command: seeds core + inventory + sales + invoicing
docker compose exec web python manage.py seed_all
```

This creates: 1 tenant, 3 branches, 4 roles, 5 users (admin@gravitea-demo.com / admin123), 100 products, 4 customers, sale orders, ARCA credentials, DRAFT invoices, and more. See [TEST-ERP-WORKFLOW.md](TEST-ERP-WORKFLOW.md) for the full testing guide.

Setting `SEED_DATA=true` on the `web` service runs `seed_all` automatically on startup (seeds core data, inventory, sales, and invoicing).

To reseed from scratch:

```bash
docker compose exec web python manage.py seed_all --clear
```

### Open the Frontend

1. Open http://localhost:3000 — you'll be redirected to `/login`
2. Enter the email and password of the superuser you created
3. After login, the sidebar shows all 6 modules

### Stop Everything

```bash
docker compose down          # Stop containers (keep data)
docker compose down -v       # Stop and delete all data (fresh start)
```

## Docker Compose Commands

All commands run from the **repository root**.

| Command | What It Does |
|---------|-------------|
| `docker compose up -d` | Start full stack with hot-reload frontend on port 3000 |
| `docker compose --profile prod up -d` | Full stack + production frontend build on port 3001 |
| `docker compose --profile observability up -d` | Full stack + Prometheus, Grafana, Jaeger, Loki, Alertmanager |
| `docker compose --profile test up -d` | Test stack (separate postgres, redis, backend, jaeger, prometheus) |
| `docker compose --profile test --profile load up -d` | Test stack + Locust load testing on port 8089 |
| `docker compose up -d web postgres redis` | Backend only (no frontend) |
| `docker compose down` | Stop all services (preserves data volumes) |
| `docker compose down -v` | Stop and destroy volumes (full reset) |
| `docker compose logs -f web` | Follow backend logs |
| `docker compose logs -f frontend` | Follow frontend logs |
| `docker compose exec web python manage.py createsuperuser` | Create a user |
| `docker compose exec web python manage.py migrate` | Run migrations manually |
| `docker compose build --no-cache` | Rebuild all images from scratch |

## Frontend Modes

The default frontend is a **dev server with hot reload** — file changes in `frontend-prototype/` reflect instantly on http://localhost:3000.

To test the production build instead:

```bash
# Stop the dev frontend and start the production build on port 3001
docker compose stop frontend
docker compose --profile prod up -d frontend-prod
```

| Mode | Port | Hot Reload | Use When |
|------|------|-----------|----------|
| `frontend` (default) | 3000 | Yes (volume mount) | Development, testing, daily use |
| `frontend-prod` (profile: prod) | 3001 | No (production build) | Final verification, Docker image testing |

The dev server uses `WATCHPACK_POLLING=true` for file watching over Docker volume mounts.

## Local Development (Without Docker)

If you prefer running services directly on your machine:

### Start PostgreSQL and Redis

```bash
# PostgreSQL — ensure it's running on port 5432
# Default dev credentials: user=gravitea, password=gravitea, db=gravitea_dev

# Redis — ensure it's running on port 6379
redis-server
```

### Start the Backend

```bash
cd backend

# Create .env from example (first time only)
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum

# Activate the virtual environment matching your terminal:
#   WSL2:    source venv-wsl/bin/activate
#   Windows: venv\Scripts\activate

python manage.py migrate
python manage.py createsuperuser   # First time only
python manage.py runserver         # Starts on http://localhost:8000
```

### Which virtual environment?

| Terminal | Venv | Activate command |
|----------|------|-----------------|
| **WSL2** (Ubuntu, Claude Code) | `backend/venv-wsl/` | `source backend/venv-wsl/bin/activate` |
| **Windows** (PowerShell, CMD) | `backend/venv/` | `backend\venv\Scripts\activate` |

**Why two?** The Windows Python binary crashes (`0xc0000005`) when invoked from WSL. The `venv-wsl/` uses Python 3.13.12 from the deadsnakes PPA with full package parity minus `pywin32`.

### Start the Frontend

```bash
cd frontend-prototype

# Install dependencies (first time only)
npm install

# Create local env file (first time only)
cp .env.example .env.local

# Start dev server
npm run dev     # http://localhost:3000
```

## Application Modules

After logging in, the sidebar provides navigation to all 6 modules:

| Route | Module | What It Does |
|-------|--------|-------------|
| `/health` | Health | Backend connectivity check with response time |
| `/auth-admin` | Auth Admin | User management, branches (read-only), roles CRUD, token operations |
| `/inventario` | Inventory | Products, categories (tree view), suppliers, stock movements, price lists, price/cost history |
| `/ventas` | Sales | Customers, sale orders with nested items, status transitions (Confirm/Authorize), invoice linking |
| `/facturacion` | Invoicing | ARCA credentials, puntos de venta, comprobante emission/authorization, QR codes, CAEA lifecycle |
| `/sync` | Sync | Device sessions, push/pull operations, device status check |

## Environment Variables

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL as seen by the **browser** (not container-to-container). In Docker Compose this is pre-configured. |

### Backend (key variables — see `backend/.env.example` for full list)

| Variable | Docker Default | Description |
|----------|---------------|-------------|
| `SECRET_KEY` | Set in compose | Django signing key |
| `DATABASE_URL` | `postgresql://gravitea:gravitea@postgres:5432/gravitea_dev` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed CORS origins |
| `SEED_DATA` | `false` | Set `true` to run `seed_all` on startup (core + inventory + sales + invoicing) |

## How Authentication Works

1. User submits email/password on `/login`
2. Frontend calls `POST /api/v1/auth/token/` and receives `{access, refresh}` tokens
3. Tokens are stored **in React state only** (no localStorage, no cookies)
4. Every API request includes `Authorization: Bearer <access_token>` via the fetch wrapper
5. On 401 response, the interceptor automatically tries `POST /api/v1/auth/token/refresh/`
6. If refresh fails, user is redirected back to `/login`
7. Concurrent 401s are deduplicated — only one refresh request is made

## Architecture

```
frontend-prototype/
  src/
    app/
      layout.tsx                    # Root layout with Providers
      login/page.tsx                # Login page (email + password)
      (protected)/
        layout.tsx                  # Auth guard + sidebar + header
        health/page.tsx             # Health module
        auth-admin/page.tsx         # Auth admin (users, branches, roles)
        inventario/page.tsx         # Inventory module (6 tabs)
        ventas/page.tsx             # Sales module (customers, orders)
        facturacion/page.tsx        # Invoicing module (4 tabs)
        sync/page.tsx               # Sync module (3 tabs)
    components/
      data-table.tsx                # Generic table with "Load More" pagination
      crud-form.tsx                 # Dynamic form with field-level errors
      confirm-dialog.tsx            # Delete confirmation dialog
      raw-json-toggle.tsx           # Collapsible raw JSON response viewer
      error-boundary.tsx            # React error boundary with retry
      status-badge.tsx              # Color-coded status badges
      jwt-claims.tsx                # JWT token decoder display
      auth-admin/                   # Auth admin tab components
      inventario/                   # Inventory tab components
      ventas/                       # Sales tab components
      facturacion/                  # Invoicing tab components
      sync/                         # Sync tab components
    hooks/
      use-crud.ts                   # TanStack Query CRUD operations
      use-pagination.ts             # Cursor-based infinite query
    lib/
      api-client.ts                 # Fetch wrapper with auth + 401 interceptor
      auth-context.tsx              # JWT auth state (tokens in memory only)
      providers.tsx                 # QueryClient + Auth + Toaster providers
      utils.ts                      # Utility functions (cn)
```

## Docker Architecture

```
docker-compose.yml (repo root — single file, all profiles)
  |
  |-- postgres:18-alpine             :5432   PostgreSQL database
  |-- redis:7-alpine                 :6379   Redis cache
  |-- web (backend/Dockerfile)       :8000   Django API (maps to internal :8080)
  |-- frontend (node:22-alpine)       :3000   Next.js dev server (hot reload)
  +-- frontend-prod (profile:prod)   :3001   Next.js standalone build
  |
  |-- [profile: observability]
  |   |-- prometheus                 :9090   Metrics collection
  |   |-- grafana                    :3002   Dashboards (admin/admin)
  |   |-- jaeger                     :16686  Distributed tracing
  |   |-- loki                       :3100   Log aggregation
  |   |-- promtail                   —       Log shipping agent
  |   +-- alertmanager               :9093   Alert routing
  |
  |-- [profile: test]
  |   |-- postgres-test              :5433   Test database
  |   |-- redis-test                 :6380   Test cache
  |   |-- web-test                   :8001   Test backend
  |   |-- jaeger-test                :16687  Test tracing
  |   +-- prometheus-test            :9091   Test metrics
  |
  +-- [profile: load (requires test)]
      +-- locust                     :8089   Load testing UI
```

The backend uses a `bootstrap.sh` entrypoint that:
1. Waits for PostgreSQL to be ready
2. Runs pre-migrate SQL (roles, extensions)
3. Runs Django migrations
4. Runs post-migrate SQL (RLS policies, functions, constraints)
5. Optionally seeds data (`seed_all`: core + inventory + sales + invoicing)
6. Starts the application (gunicorn in prod, `runserver` in dev)

## Production Notes

This Docker setup approximates the production topology:
- **Cloud Run** will run the backend (gunicorn) and frontend (standalone Node.js) as separate services
- **Cloud SQL** replaces the local PostgreSQL container
- The `NEXT_PUBLIC_API_URL` build arg will point to the Cloud Run backend URL in production

## Troubleshooting

| Problem | Solution |
|---------|----------|
| CORS errors in browser console | Backend dev settings have `CORS_ALLOW_ALL_ORIGINS = True`. Check that `NEXT_PUBLIC_API_URL` matches the backend URL (default: `http://localhost:8000`). |
| 401 Unauthorized on every request | Create a user: `docker compose exec web python manage.py createsuperuser` |
| Empty tables / no data | Seed data: `docker compose exec web python manage.py seed_all` or create through the UI. |
| "Failed to fetch" errors | Backend is not running. Check: `docker compose ps` and `docker compose logs web` |
| Port 3000 already in use | Stop the conflicting service, or use the dev frontend on port 3001: `docker compose --profile dev up -d frontend-dev` |
| Login succeeds but redirects back | Check backend logs: `docker compose logs -f web`. Ensure `SECRET_KEY` is set. |
| Frontend shows old code after changes | Rebuild: `docker compose build frontend` then `docker compose up -d frontend` |
| Backend migrations fail | Check logs: `docker compose logs web`. For "already exists" errors, fake the migration: `docker compose exec web python manage.py migrate <app> <migration> --fake` |
| Docker build slow | First build downloads base images. Subsequent builds use cache. Use `docker compose build` to pre-build. |
| Volume mount file watching not working | The dev profile uses `WATCHPACK_POLLING=true`. Restart: `docker compose --profile dev restart frontend-dev` |
| Observability services not starting | Run: `docker compose --profile observability up -d`. All services are in a single compose file. |
