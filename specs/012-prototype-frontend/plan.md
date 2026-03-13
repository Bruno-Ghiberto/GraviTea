# Implementation Plan: Prototype Frontend for Backend API Testing

**Branch**: `012-prototype-frontend` | **Date**: 2026-02-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/012-prototype-frontend-prototype/spec.md`

## Summary

Build a developer-only prototype frontend using Next.js 15 (App Router) + TypeScript + shadcn/ui to interact with all 62 GRAVITEA-ERP backend API endpoints across 6 modules (auth, health, inventario, ventas, facturacion, sync). The frontend stores JWT tokens in memory only, provides module-per-page navigation with sidebar, and includes raw JSON inspection on every API response. Scope: ~15 page components, ~10 shared components, 1 Dockerfile, ~46 tasks across 10 phases.

## Technical Context

**Language/Version**: TypeScript 5.x (strict mode), Node.js 20+ LTS
**Primary Dependencies**: Next.js 15 (App Router), React 19, shadcn/ui, TanStack Query v5, Tailwind CSS 4, native fetch
**Storage**: In-memory only (React Context for JWT tokens) — no database, no localStorage
**Testing**: None (per A-005: the prototype IS the testing tool)
**Target Platform**: Docker container (standalone Next.js output), browser-only (Chrome/Firefox/Edge)
**Project Type**: Web application (frontend consuming existing backend API)
**Performance Goals**: Page load under 1 second on localhost (SC-006), Docker image under 200MB (SC-008), build under 60 seconds (SC-008)
**Constraints**: Must exercise all 62 backend endpoints (SC-001), in-memory token storage only (FR-020), field-level error display (FR-016), raw JSON on every response (FR-017)
**Scale/Scope**: ~15 page/tab components, ~10 shared components, 6 module pages, 62 API endpoint integrations, 0 backend changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Ironclad Data Model | N/A | Frontend does not define data models — backend owns all schema, constraints, and financial precision. Frontend displays what the API returns. |
| II | Multi-Tenant Isolation | PASS | Frontend sends JWT with tenant_id/branch_id claims on every request. No direct DB access. Tenant scoping is enforced entirely by the backend RLS layer. |
| III | Modular Django Architecture | N/A | This feature is a Next.js frontend — it does not modify the Django backend module structure. |
| IV | Application-Level Encryption | N/A | Frontend does not handle encryption. All PII encryption/decryption occurs server-side. Frontend receives already-decrypted display values from the API. |
| V | Secure Authentication & Sessions | PASS | JWT tokens stored in memory only (FR-020). No persistent storage (localStorage/cookies forbidden). Automatic token refresh on 401 (FR-019). Token claims displayed for developer inspection. |
| VI | Fiscal Compliance (ARCA) | PASS | Frontend displays ARCA responses transparently including error codes (US-5 SC-8). It does not bypass or modify fiscal data — all ARCA operations are backend-mediated. |
| VII | Offline-First & Contingency | N/A | Prototype is online-only. Offline-first support is reserved for the production Electron client (documented in `frontend-prototype/AGENTS.MD`). |
| VIII | Query Optimization | N/A | No database queries originate from the frontend. Backend handles all query optimization. Frontend uses cursor pagination to avoid requesting excessive data. |
| IX | Secure Data Operations | PASS | Frontend sends form data to backend endpoints. Backend enforces field allowlists, mass assignment protection, and permission checks. Frontend displays validation errors returned by the API. |
| X | Test-Driven Development | N/A | Per A-005: "No testing framework is needed for the prototype itself — it IS the testing tool." The prototype validates backend functionality by exercising all 62 endpoints. |
| XI | JWT Authentication | PASS | Frontend consumes JWT tokens from the backend auth endpoint. Displays decoded claims (tenant_id, user_id, exp) per FR-004. Handles 15-min access token expiry via automatic refresh (FR-019). |
| XII | Rate Limiting Strategy | N/A | Rate limiting is enforced by the backend. Frontend handles 429 responses by displaying the error to the developer (covered by FR-018 error handling). |
| XIII | Cursor-Based Pagination | PASS | Frontend implements "Load More" button pattern (FR-022) using the backend's cursor-based pagination. Follows default 100 items, passes cursor parameter for next page. |
| XIV | API Documentation | PASS | Frontend is built FROM the 6 OpenAPI specs in `api/openapi/`. Using the prototype validates that the API documentation matches actual behavior — a living documentation test. |

**Result**: All applicable gates PASS. 7 principles are N/A (frontend-only feature). No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/012-prototype-frontend-prototype/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (tech decisions)
├── quickstart.md        # Setup and verification guide
└── tasks.md             # speckit.tasks output (NOT created here)
```

### Source Code (repository root)

```text
frontend-prototype/
├── AGENTS.MD                        # Existing — production Electron plans
├── README.md                        # ENHANCED — updated with prototype info
├── package.json                     # NEW — Next.js 15 + dependencies
├── tsconfig.json                    # NEW — TypeScript strict config
├── next.config.ts                   # NEW — standalone output, API rewrites
├── tailwind.config.ts               # NEW — Tailwind CSS 4 config
├── components.json                  # NEW — shadcn/ui config
├── Dockerfile                       # NEW — multi-stage standalone build
├── .env.example                     # NEW — NEXT_PUBLIC_API_URL template
├── public/                          # NEW
│   └── favicon.ico
├── src/
│   ├── app/                         # NEW — App Router pages
│   │   ├── layout.tsx               # Root layout with providers
│   │   ├── login/
│   │   │   └── page.tsx             # Login page
│   │   ├── (protected)/             # Route group (requires auth)
│   │   │   ├── layout.tsx           # Sidebar + header layout
│   │   │   ├── health/
│   │   │   │   └── page.tsx         # Health check dashboard
│   │   │   ├── auth-admin/
│   │   │   │   └── page.tsx         # Users, Branches, Roles tabs
│   │   │   ├── inventario/
│   │   │   │   └── page.tsx         # Products, Categories, Suppliers, etc.
│   │   │   ├── ventas/
│   │   │   │   └── page.tsx         # Customers, Sale Orders
│   │   │   ├── facturacion/
│   │   │   │   └── page.tsx         # Credentials, Comprobantes, CAEA
│   │   │   └── sync/
│   │   │       └── page.tsx         # Sessions, Push/Pull, Status
│   │   └── not-found.tsx            # 404 handler
│   ├── components/                  # NEW — shared components
│   │   ├── ui/                      # shadcn/ui generated components
│   │   ├── data-table.tsx           # Generic table with Load More
│   │   ├── crud-form.tsx            # Generic form with field errors
│   │   ├── raw-json-toggle.tsx      # Raw JSON display toggle
│   │   ├── status-badge.tsx         # Color-coded status indicator
│   │   ├── confirm-dialog.tsx       # Confirmation for destructive actions
│   │   ├── sidebar-nav.tsx          # Module navigation sidebar
│   │   └── jwt-claims.tsx           # Decoded JWT claims display
│   ├── lib/                         # NEW — utilities
│   │   ├── api-client.ts            # Fetch wrapper with JWT injection
│   │   ├── auth-context.tsx         # AuthProvider + useAuth hook
│   │   ├── query-client.tsx         # TanStack Query provider
│   │   └── utils.ts                 # shadcn/ui cn() utility
│   └── hooks/                       # NEW — custom hooks
│       ├── use-crud.ts              # Generic CRUD hook (list, create, update, delete)
│       └── use-pagination.ts        # Cursor pagination hook with Load More
└── components/                      # (empty — shadcn/ui uses src/components/ui/)

backend/
├── docker-compose.yml               # ENHANCED — add frontend service with profile
```

## Phase 1: Project Scaffolding (7 tasks)

Initialize the Next.js project with all dependencies, configuration, and Docker setup.

**Dependencies**: None
**Covers**: SC-006, SC-008, project foundation

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 1.1 | Initialize Next.js project | Run `create-next-app` with TypeScript, App Router, Tailwind CSS, src/ directory in `frontend-prototype/` | No (first task) |
| 1.2 | Configure TypeScript strict mode | Update `tsconfig.json` with strict: true, path aliases (`@/` → `src/`) | After 1.1 |
| 1.3 | Install shadcn/ui | Run `npx shadcn@latest init`, install base components: button, input, card, table, dialog, tabs, badge, separator, toast | After 1.1 |
| 1.4 | Install TanStack Query v5 | `npm install @tanstack/react-query @tanstack/react-query-devtools` | After 1.1 |
| 1.5 | Create next.config.ts | Configure `output: 'standalone'`, set up `rewrites` for API proxy (optional dev convenience) | After 1.1 |
| 1.6 | Create Dockerfile | Multi-stage build: deps → build → standalone runner. Target image <200MB. Add to docker-compose.yml with `frontend` profile | After 1.5 |
| 1.7 | Create .env.example | `NEXT_PUBLIC_API_URL=http://localhost:8000` template file | Yes |

**Validation Gate**: `npm run build` succeeds, `docker build` produces image <200MB, dev server starts on port 3000.

## Phase 2: Auth System & Layout Shell (7 tasks)

Implement JWT authentication (login, refresh, logout), protected route wrapper, and the sidebar navigation layout.

**Dependencies**: Phase 1
**Covers**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-020

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 2.1 | Create AuthContext | `src/lib/auth-context.tsx`: AuthProvider storing access/refresh tokens in React state (memory only). Provide `login()`, `logout()`, `refresh()`, `isAuthenticated`, `claims` (decoded JWT payload). | No (foundation) |
| 2.2 | Create API client | `src/lib/api-client.ts`: Fetch wrapper that reads token from AuthContext and injects `Authorization: Bearer <token>` header on every request. Base URL from `NEXT_PUBLIC_API_URL`. | After 2.1 |
| 2.3 | Create TanStack Query provider and wire layout | `src/lib/query-client.tsx`: QueryClientProvider. Configure default staleTime, retry, error handling. Wire AuthProvider + QueryClientProvider into `src/app/layout.tsx`. | After 2.1 |
| 2.4 | Create login page | `src/app/login/page.tsx`: Email + password form using shadcn/ui Card + Input + Button. On success, store tokens via AuthContext, redirect to `/health`. On error, display backend error message. | After 2.1, 2.2 |
| 2.5 | Create protected layout with sidebar | `src/app/(protected)/layout.tsx`: Check `isAuthenticated` — redirect to `/login` if false. Render sidebar (links to all 6 modules) + header (user info, logout button) + main content area. | After 2.1 |
| 2.6 | Create JWT claims display | `src/components/jwt-claims.tsx`: Decode the access token (base64 payload) and display tenant_id, user_id, email, exp as a small info card. Show in header or auth page. | After 2.1 |
| 2.7 | Implement profile, refresh, verify, change password, logout | Add to auth page: profile view (GET /auth/users/me/), manual refresh button (POST /auth/token/refresh/), token verify (POST /auth/token/verify/), change password form (POST /auth/users/me/change-password/), logout button (POST /auth/logout/). | After 2.2, 2.4 |

**Validation Gate**: Developer can log in, see decoded JWT claims, navigate sidebar to all 6 modules, refresh token, change password, and log out. Unauthenticated access redirects to login.

## Phase 3: Shared UI Components (6 tasks)

Build the reusable components that every module page will use: data tables, forms, error display, and raw JSON toggle.

**Dependencies**: Phase 2
**Covers**: FR-016, FR-017, FR-018, FR-022

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 3.1 | Create DataTable component | `src/components/data-table.tsx`: Generic table using shadcn/ui Table. Props: columns config, data array, isLoading, onLoadMore callback, hasNextPage boolean. Renders "Load More" button at bottom for cursor pagination. | Yes |
| 3.2 | Create CrudForm and ConfirmDialog components | `src/components/crud-form.tsx`: Generic form rendering fields from a config array. Displays field-level validation errors from backend (maps `{field: [errors]}` to inline messages). Supports create and edit modes. `src/components/confirm-dialog.tsx`: Confirmation dialog for destructive actions (delete). | Yes |
| 3.3 | Create RawJsonToggle component | `src/components/raw-json-toggle.tsx`: Collapsible section showing raw JSON of any API response. Uses shadcn/ui Collapsible + pre/code block with syntax formatting. | Yes |
| 3.4 | Create ErrorBoundary component | React error boundary at the app level. Catches unexpected errors and displays the raw error details instead of a white screen. Also handles network errors from failed API calls. | Yes |
| 3.5 | Create StatusBadge component | `src/components/status-badge.tsx`: Color-coded badge (green/yellow/red/gray) for entity states (order status, health status, CAEA status). | Yes |
| 3.6 | Create generic CRUD and pagination hooks | `src/hooks/use-crud.ts`: Hook wrapping TanStack Query for list (with cursor pagination), create, update, delete mutations for any endpoint. `src/hooks/use-pagination.ts`: Infinite query hook with "Load More" support. | Yes |

**Validation Gate**: All shared components render correctly in isolation. DataTable shows "Load More", CrudForm displays field errors from a mock error response, RawJsonToggle shows/hides JSON.

## Phase 4: Health Module (2 tasks)

Implement the health check dashboard — the simplest module and first validation of backend connectivity.

**Dependencies**: Phase 3
**Covers**: FR-007

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 4.1 | Create health page | `src/app/(protected)/health/page.tsx`: Call GET `/health/`, display pass/fail StatusBadge, response time in ms, and summary of checks (database, cache, migrations). Include refresh button. | No (main task) |
| 4.2 | Add raw JSON detail view | Add RawJsonToggle showing the full health check JSON response. Display individual check statuses (database: pass, cache: pass, etc.). | After 4.1 |

**Validation Gate**: Health page shows green badge when backend is running, red badge when unreachable. Response time displays. Raw JSON shows full response.

## Phase 5: Auth Admin Module (3 tasks)

Implement the admin section of the auth page: Users, Branches, and Roles management.

**Dependencies**: Phase 3
**Covers**: FR-021

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 5.1 | Create Users tab | Tab within auth-admin page: DataTable listing users (email, name, role, branch, active). CrudForm for create/edit. Delete with confirmation. Endpoints: GET/POST `/auth/users/`, GET/PUT/DELETE `/auth/users/{id}/`. | Yes |
| 5.2 | Create Branches tab | Tab listing branches (name, address, active). Detail view on row click. Read-only — no create/edit/delete. Endpoints: GET `/auth/branches/`, GET `/auth/branches/{id}/`. | Yes |
| 5.3 | Create Roles tab | Tab listing roles (name, permissions). CrudForm for create/edit. Delete with confirmation. Endpoints: GET/POST `/auth/roles/`, GET/PUT/DELETE `/auth/roles/{id}/`. | Yes |

**Validation Gate**: All three tabs render with data from the backend. Users and Roles support full CRUD. Branches show list and detail. All responses have RawJsonToggle.

## Phase 6: Inventory Module (6 tasks)

Implement the largest module with 19 endpoints: products, categories, suppliers, stock movements, price lists, and history.

**Dependencies**: Phase 3
**Covers**: FR-008, FR-009, FR-010, FR-011

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 6.1 | Create Products tab | DataTable with product list (name, SKU, category, stock level). CRUD form. Search via POST `/products/search/`. Stock level display from product detail. Endpoints: GET/POST `/products/`, GET/PUT/DELETE `/products/{id}/`, GET `/products/{id}/stock/`. | Yes |
| 6.2 | Create Categories tab | DataTable with category list. CRUD form with optional parent_id for nesting. Tree view via GET `/categories/tree/`. Endpoints: GET/POST `/categories/`, GET/PUT/DELETE `/categories/{id}/`, GET `/categories/tree/`. | Yes |
| 6.3 | Create Suppliers tab | DataTable with supplier list. CRUD form. Search via GET `/suppliers/search/`. Endpoints: GET/POST `/suppliers/`, GET/PUT/DELETE `/suppliers/{id}/`, GET `/suppliers/search/`. | Yes |
| 6.4 | Create Stock Movements tab | DataTable showing movements (product, quantity, type, date). Create-only form (no edit, no delete — immutable ledger). Endpoints: GET/POST `/movements/`, GET `/movements/{id}/`. | Yes |
| 6.5 | Create Price Lists tab | DataTable with price lists. CRUD form. "Set as default" action button. Endpoints: GET/POST `/price-lists/`, GET/PUT/DELETE `/price-lists/{id}/`, POST `/price-lists/{id}/set_default/`. | Yes |
| 6.6 | Create History tabs | Read-only DataTables for price history and cost history. No create/edit/delete. Endpoints: GET `/price-history/`, GET `/price-history/{id}/`, GET `/cost-history/`, GET `/cost-history/{id}/`. | Yes |

**Validation Gate**: All 19 inventario endpoints are exercisable. Products and suppliers support search. Stock movements are create-only (edit/delete buttons absent). Category tree renders hierarchically. Price list default can be toggled.

## Phase 7: Sales Module (4 tasks)

Implement customers, sale orders with nested items, status transitions, and invoice linking.

**Dependencies**: Phase 3
**Covers**: FR-008, FR-012

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 7.1 | Create Customers tab | DataTable with customer list (razon_social, CUIT, condicion_iva). CRUD form with CUIT validation display. Endpoints: GET/POST `/ventas/customers/`, GET/PUT/DELETE `/ventas/customers/{id}/`. | Yes |
| 7.2 | Create Sale Orders tab | DataTable with orders (number, customer, status badge, total, date). CRUD form for creating orders. Status badge using StatusBadge component. Endpoints: GET/POST `/ventas/orders/`, GET/PUT/DELETE `/ventas/orders/{id}/`. | Yes |
| 7.3 | Create nested Order Items | Within order detail view, show items DataTable (product, quantity, price, subtotal). Add/edit/delete items. Endpoints: GET/POST `/ventas/orders/{id}/items/`, GET/PATCH/DELETE `/ventas/orders/{id}/items/{item_id}/`. | After 7.2 |
| 7.4 | Add status transitions and invoice link | "Confirm" and "Authorize" action buttons on order detail (POST `/ventas/orders/{id}/confirm/`, POST `/ventas/orders/{id}/authorize/`). Display linked invoice via GET `/ventas/orders/{id}/invoice/`. | After 7.2 |

**Validation Gate**: Customer CRUD works. Orders show status badges. Items nest within order detail. Confirm/Authorize transitions change status. Invoice link displays when present.

## Phase 8: Invoicing (Facturacion) Module (4 tasks)

Implement ARCA credential management, comprobante emission, CAE authorization, QR display, and CAEA lifecycle.

**Dependencies**: Phase 3
**Covers**: FR-008, FR-010, FR-013, FR-014

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 8.1 | Create Credentials and Puntos de Venta tabs | Two tabs with CRUD: ARCA credentials (CUIT, cert name, environment) and Puntos de Venta (number, type, status). Endpoints: GET/POST/PUT/DELETE for `/facturacion/credentials/` and `/facturacion/puntos-de-venta/`. | Yes |
| 8.2 | Create Comprobantes tab | DataTable listing comprobantes (type, number, date, total, CAE status). Emit form for creating new comprobante (select punto_venta, type, customer, items/amounts). Read-only detail view. Endpoints: GET `/facturacion/comprobantes/`, POST `/facturacion/comprobantes/emitir/`, GET `/facturacion/comprobantes/{id}/`. | Yes |
| 8.3 | Add CAE authorization and QR display | "Authorize" action button on comprobante detail (POST `/facturacion/comprobantes/{id}/authorize/`). Display ARCA response (success with CAE number or error code/message). QR data display (GET `/facturacion/comprobantes/{id}/qr/`). | After 8.2 |
| 8.4 | Create CAEA tab | DataTable listing CAEAs (GET `/facturacion/caeas/`). Detail view (GET `/facturacion/caeas/{id}/`). "Request CAEA" form (POST `/facturacion/caeas/solicitar/`). "Sin Movimiento" action on CAEA row (POST `/facturacion/caeas/{id}/sin-movimiento/`). | Yes |

**Validation Gate**: All 13 facturacion endpoints exercisable. Comprobante emit form works (even if ARCA returns error without real certs — error is displayed). CAEA request and sin-movimiento actions work. QR data displays for authorized comprobantes.

## Phase 9: Sync Module (3 tasks)

Implement sync session management, push/pull operations, and device status checking.

**Dependencies**: Phase 3
**Covers**: FR-015

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 9.1 | Create Sync Sessions tab | DataTable listing sessions (device_id, status, created_at). Create session form. Delete (close) session. Endpoints: GET/POST `/sync/sessions/`, GET/DELETE `/sync/sessions/{id}/`. | No (main task) |
| 9.2 | Add Push/Pull operations | Two action buttons on session detail: "Push" (POST `/sync/push/`) and "Pull" (POST `/sync/pull/`). Display request and response payloads using RawJsonToggle. | After 9.1 |
| 9.3 | Add Device Status check | Input field for device_id, "Check Status" button. Calls GET `/sync/status/{device_id}/`. Displays sync status details. | Yes (with 9.1) |

**Validation Gate**: All 5 sync endpoints exercisable. Push/pull payloads visible. Device status returns data. Session create/delete works.

## Phase 10: Integration & Hardening (4 tasks)

Implement automatic token refresh retry, global error handling, and end-to-end Docker validation.

**Dependencies**: Phases 4-9
**Covers**: FR-018, FR-019, SC-001, SC-008

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 10.1 | Implement 401 interceptor with token refresh | In api-client.ts: on 401 response, automatically call refresh endpoint, retry the original request with new token. If refresh fails, redirect to login. Handles the edge case of mid-session token expiry. | No (affects all API calls) |
| 10.2 | Add global error boundary | Wrap app in ErrorBoundary that catches React errors and unhandled API errors. Display raw error response body. Prevent white-screen crashes (e.g., trying to delete an authorized comprobante returns backend error, not a client crash). | After 10.1 |
| 10.3 | Docker compose end-to-end validation | Build frontend image, verify size <200MB (SC-008), build time <60s. Start full stack via `docker compose --profile frontend up`. Verify frontend connects to backend through Docker network. | After 10.1 |
| 10.4 | Endpoint coverage walkthrough | Manual verification that all 62 endpoints are exercisable through the UI. Document any endpoints that require specific data states. Update quickstart.md if needed. | After 10.3 |

**Validation Gate**: Token refresh works transparently (access token expiry doesn't interrupt workflow). Error boundary catches and displays unexpected errors. Docker image <200MB, builds <60s. All 62 endpoints confirmed accessible.

## Task Summary

| Phase | Name | Tasks | Cumulative |
|-------|------|-------|------------|
| 1 | Project Scaffolding | 7 | 7 |
| 2 | Auth System & Layout Shell | 7 | 14 |
| 3 | Shared UI Components | 6 | 20 |
| 4 | Health Module | 2 | 22 |
| 5 | Auth Admin Module | 3 | 25 |
| 6 | Inventory Module | 6 | 31 |
| 7 | Sales Module | 4 | 35 |
| 8 | Invoicing Module | 4 | 39 |
| 9 | Sync Module | 3 | 42 |
| 10 | Integration & Hardening | 4 | 46 |
| **Total** | | **46** | |

## Parallelization Opportunities

- **Phases 4 + 5 + 6 + 7 + 8 + 9**: All module pages can execute in parallel once Phases 1-3 (scaffolding, auth, shared components) are complete. Each module page is independent.
- **Phase 3**: All 6 shared component tasks are independent and can be built in parallel.
- **Phase 5**: All 3 auth admin tabs are independent.
- **Phase 6**: All 6 inventory sub-tabs are independent.
- **Phase 1**: Tasks 1.3 and 1.4 (install shadcn, install TanStack Query) can run in parallel after 1.1.

**Optimal parallel execution**: Phases 1-3 sequential (~20 tasks), then Phases 4-9 all parallel (~22 tasks), then Phase 10 sequential (~4 tasks). With 3 agents on Phases 4-9, the module pages complete in roughly the time of the largest (Phase 6, 6 tasks).

## Integration Checkpoints

| After Phase | Checkpoint | Action |
|-------------|-----------|--------|
| 1 | Project builds and Docker image <200MB | `npm run build` + `docker build` — verify no errors, measure image size |
| 2 | Auth flow works end-to-end | Log in with seeded user, verify JWT claims display, navigate sidebar, log out |
| 3 | Shared components render correctly | Visually verify DataTable, CrudForm, RawJsonToggle, ErrorBoundary with mock data |
| 6 | Largest module (inventario) fully functional | Exercise all 19 inventario endpoints through the UI, verify search and tree view |
| 9 | All 6 modules implemented | Navigate to each module, verify at least one operation works per module |
| 10 | Full stack Docker validation | `docker compose --profile frontend up`, verify frontend → backend connectivity, exercise all 62 endpoints |

## FR Coverage Matrix

| FR | Phase | Task(s) | Description |
|----|-------|---------|-------------|
| FR-001 | 2 | 2.1, 2.4 | JWT authentication via email/password login |
| FR-002 | 2 | 2.2 | Automatic JWT injection in every API request |
| FR-003 | 2 | 2.5 | Redirect unauthenticated users to login |
| FR-004 | 2 | 2.6 | Display decoded JWT claims (tenant_id, user_id, exp) |
| FR-005 | 2 | 2.7 | Token refresh, verify, change password, profile view, logout |
| FR-006 | 2 | 2.5 | Sidebar navigation to all 6 modules |
| FR-007 | 4 | 4.1, 4.2 | Health status with pass/fail badge and response time |
| FR-008 | 5, 6, 7, 8 | 5.1-5.3, 6.1-6.5, 7.1-7.2, 8.1-8.2 | Full CRUD for products, categories, suppliers, price lists, customers, orders, items, credentials, puntos de venta |
| FR-009 | 6 | 6.4 | Create-only (immutable) stock movements |
| FR-010 | 6, 8 | 6.6, 8.2 | Read-only views for price/cost history and comprobante details |
| FR-011 | 6 | 6.1, 6.2, 6.3 | Product search, supplier search, category tree viewing |
| FR-012 | 7 | 7.4 | Sale order status transitions (confirm, authorize) and linked invoice |
| FR-013 | 8 | 8.2, 8.3 | Comprobante emission, CAE authorization, fiscal QR display |
| FR-014 | 8 | 8.4 | CAEA listing, requesting new CAEAs, sin-movimiento reporting |
| FR-015 | 9 | 9.1, 9.2, 9.3 | Sync session management, push/pull, device status |
| FR-016 | 3 | 3.2 | Field-level validation error display on forms |
| FR-017 | 3 | 3.3 | Raw JSON toggle on every API response |
| FR-018 | 3, 10 | 3.4, 10.2 | Graceful error handling with raw error display |
| FR-019 | 10 | 10.1 | Automatic token refresh on 401 before redirect |
| FR-020 | 2 | 2.1 | Tokens stored in memory only — no persistent storage |
| FR-021 | 5 | 5.1, 5.2, 5.3 | Users/Roles CRUD and Branches read-only on auth page |
| FR-022 | 3 | 3.1, 3.6 | "Load More" button with cursor-based pagination |

**Coverage**: All 22 FRs mapped. No gaps.

## Complexity Tracking

No constitution violations to justify. All design decisions align with established principles. The frontend operates purely as an API consumer — all security, isolation, and data integrity enforcement remains in the backend.
