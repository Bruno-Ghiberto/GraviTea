# Quickstart: Prototype Frontend

**Branch**: `012-prototype-frontend` | **Date**: 2026-02-17

## Prerequisites

- Node.js 20+ (LTS) installed
- Backend API running at `http://localhost:8000` (via Docker Compose or manual)
- At least one seeded tenant with a user account (run `python manage.py seed_ventas` in backend)

## Local Development (without Docker)

```bash
# From repo root
cd frontend-prototype

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Default: NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Open `http://localhost:3000` in your browser.

## Docker Development

```bash
# From repo root — starts backend + frontend together
docker compose --profile frontend up --build

# Or just the frontend (backend already running)
docker compose --profile frontend up --build frontend
```

Frontend available at `http://localhost:3000`.

## Verify It Works

1. Open `http://localhost:3000` — should redirect to `/login`
2. Enter credentials for a seeded user (e.g., `admin@tenant1.com` / password from seed)
3. After login, decoded JWT claims should display (tenant_id, user_id, exp)
4. Navigate to Health — green badge confirms backend connectivity
5. Navigate to any module — tables load with "Load More" pagination
6. Click "Raw JSON" on any response to see the full payload

## Key Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with hot reload (port 3000) |
| `npm run build` | Production build (standalone output) |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint checks |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## Troubleshooting

- **CORS errors**: Ensure backend `docker-compose.yml` has `CORS_ALLOWED_ORIGINS` including `http://localhost:3000` (already configured).
- **401 on every request**: Check that the backend has at least one seeded user and the JWT keys are configured.
- **Empty tables**: Run `python manage.py seed_ventas` in the backend to populate test data.
- **Port 3000 in use**: Change the port with `npm run dev -- -p 3001` and update `CORS_ALLOWED_ORIGINS` in backend.

## Endpoint Coverage

The prototype covers **48 of 87 unique method+path combinations** (55%) across all 6 modules. Coverage prioritizes list views, create actions, and module-specific workflows over individual detail/update/delete operations.

### Coverage by Module

| Module | Covered | Total | % | Notes |
|--------|---------|-------|---|-------|
| Health | 1 | 1 | 100% | GET /health/ |
| Auth | 10 | 17 | 59% | login, logout, refresh, verify, profile, change-password, users list, branches list, roles CRUD |
| Inventario | 13 | 33 | 39% | products list+create, categories tree+create, suppliers list+create, movements list+create, price-lists CRUD+set_default, price/cost history list |
| Ventas | 9 | 20 | 45% | customers list+create, orders list+create+detail, items list+create, confirm+authorize actions |
| Facturacion | 11 | 21 | 52% | comprobantes list+detail+emitir+authorize+qr, credentials list+create, puntos-venta CRUD, caeas list+solicitar+sin-movimiento |
| Sync | 7 | 8 | 88% | sessions list+register+unregister, pull, push, device status |
| **Total** | **51** | **100** | **51%** | |

### Covered Endpoints Detail

**Auth** (10/17)
- `POST /api/v1/auth/token/` — login (auth-context.tsx)
- `POST /api/v1/auth/token/refresh/` — refresh (auth-context.tsx)
- `POST /api/v1/auth/token/verify/` — verify (operations-tab.tsx)
- `POST /api/v1/auth/logout/` — logout (auth-context.tsx)
- `GET /api/v1/auth/users/me/` — profile (operations-tab.tsx)
- `POST /api/v1/auth/users/me/change-password/` — change password (operations-tab.tsx)
- `GET /api/v1/auth/users/` — list (users-tab.tsx)
- `GET /api/v1/auth/branches/` — list (branches-tab.tsx)
- `GET /api/v1/auth/roles/` + `POST` — list+create (roles-tab.tsx)
- `PATCH /api/v1/auth/roles/{id}/` + `DELETE` — update+delete (roles-tab.tsx)

**Inventario** (13/33)
- `GET /api/v1/products/` + `POST` — list+create (products-tab.tsx)
- `GET /api/v1/categories/tree/` + `POST /categories/` — tree+create (categories-tab.tsx)
- `GET /api/v1/suppliers/` + `POST` — list+create (suppliers-tab.tsx)
- `GET /api/v1/movements/` + `POST` — list+create (movements-tab.tsx)
- `GET /api/v1/price-lists/` + `POST` + `PATCH /{id}/` + `DELETE /{id}/` — CRUD (price-lists-tab.tsx)
- `POST /api/v1/price-lists/{id}/set_default/` — action (price-lists-tab.tsx)
- `GET /api/v1/price-history/` — list (history-tabs.tsx)
- `GET /api/v1/cost-history/` — list (history-tabs.tsx)

**Ventas** (9/20)
- `GET /api/v1/ventas/customers/` + `POST` — list+create (customers-tab.tsx)
- `GET /api/v1/ventas/orders/` + `POST` — list+create (orders-tab.tsx)
- `GET /api/v1/ventas/orders/{id}/` — detail (orders-tab.tsx)
- `POST /api/v1/ventas/orders/{id}/confirm/` — action (orders-tab.tsx)
- `POST /api/v1/ventas/orders/{id}/authorize/` — action (orders-tab.tsx)
- `GET /api/v1/ventas/orders/{order_pk}/items/` + `POST` — list+create (orders-tab.tsx)

**Facturacion** (11/21)
- `GET /api/v1/facturacion/comprobantes/` — list (comprobantes-tab.tsx)
- `POST /api/v1/facturacion/comprobantes/emitir/` — emit (comprobantes-tab.tsx)
- `GET /api/v1/facturacion/comprobantes/{id}/` — detail (comprobantes-tab.tsx)
- `POST /api/v1/facturacion/comprobantes/{id}/authorize/` — action (comprobantes-tab.tsx)
- `GET /api/v1/facturacion/comprobantes/{id}/qr/` — link (comprobantes-tab.tsx)
- `GET /api/v1/facturacion/credentials/` + `POST` — list+create (credentials-tab.tsx)
- `GET /api/v1/facturacion/puntos-de-venta/` + `POST` + `PATCH /{id}/` + `DELETE /{id}/` — CRUD (puntos-venta-tab.tsx)
- `GET /api/v1/facturacion/caeas/` — list (caea-tab.tsx)
- `POST /api/v1/facturacion/caeas/solicitar/` — action (caea-tab.tsx)
- `POST /api/v1/facturacion/caeas/{id}/sin-movimiento/` — action (caea-tab.tsx)

**Sync** (7/8)
- `GET /api/v1/sync/sessions/` + `POST` — list+register (sessions-tab.tsx)
- `DELETE /api/v1/sync/sessions/{id}/` — unregister (sessions-tab.tsx)
- `POST /api/v1/sync/pull/` — pull (operations-tab.tsx)
- `POST /api/v1/sync/push/` — push (operations-tab.tsx)
- `GET /api/v1/sync/status/{device_id}/` — status (status-tab.tsx)

### Not Covered (by design for prototype)

The uncovered endpoints fall into these categories:
- **Individual detail views** (GET /{id}/) — prototype shows data in list tables
- **Full updates** (PUT) — prototype uses PATCH for partial updates
- **Individual deletes** on non-CRUD resources — prototype focuses on list+create
- **Search endpoints** (/search/) — prototype uses pagination-based browsing
- **User CRUD admin** (POST/PATCH/DELETE /auth/users/) — prototype shows read-only list
- **Stock level check** (GET /products/{id}/stock/) — deferred to V2

### Docker Validation

| Metric | Result | Target |
|--------|--------|--------|
| Image size | 76.3 MB | < 200 MB |
| Build time | ~8s (builder stage) | < 60s |
| All routes serve 200 | 7/7 | 7/7 |
| Non-root user | nextjs:1001 | required |
