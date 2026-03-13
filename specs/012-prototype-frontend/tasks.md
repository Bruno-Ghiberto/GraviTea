# Tasks: Prototype Frontend for Backend API Testing

**Feature**: 012-prototype-frontend
**Branch**: `012-prototype-frontend`
**Status**: Ready for Implementation
**Total Tasks**: 46 (organized by phase and user story)

---

## Task Format

Each task follows this strict format:

```
- [ ] [TaskID] [P?] [Story?] Description with exact file path
```

- **Checkbox** (`- [ ]`): ALWAYS required
- **TaskID** (T001-T046): Sequential execution order
- **[P]**: Optional parallelizable marker
- **[Story]**: Optional story label ([US1], [US2], etc.)
- **Description**: Clear action with file path

---

## Phase 1: Project Scaffolding (7 tasks)

Initialize Next.js 15 with dependencies, configuration, and Docker setup.

**Validation Gate**: `npm run build` succeeds, Docker image <200MB, dev server starts on port 3000.

- [X] T001 Initialize Next.js 15 project with TypeScript, App Router, Tailwind CSS in `frontend-prototype/`
- [X] T002 Configure TypeScript strict mode and path aliases in `frontend-prototype/tsconfig.json`
- [X] T003 [P] Install shadcn/ui base components in `frontend-prototype/` (button, input, card, table, dialog, tabs, badge, separator, toast)
- [X] T004 [P] Install TanStack Query v5 with `npm install @tanstack/react-query @tanstack/react-query-devtools` in `frontend-prototype/`
- [X] T005 Create `frontend-prototype/next.config.ts` with standalone output mode and optional API rewrites
- [X] T006 Create multi-stage `frontend-prototype/Dockerfile` targeting <200MB with standalone output
- [X] T007 [P] Create `frontend-prototype/.env.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## Phase 2: Auth System & Layout Shell (7 tasks)

Implement JWT authentication and protected route layout — **BLOCKS all user story work**.

**Validation Gate**: Developer can log in, view decoded JWT claims, navigate sidebar to all 6 modules, refresh token, and log out.

- [X] T008 Create `frontend-prototype/src/lib/auth-context.tsx` with AuthProvider storing tokens in React state (memory only) and providing `login()`, `logout()`, `refresh()`, `isAuthenticated`, `claims`
- [X] T009 Create `frontend-prototype/src/lib/api-client.ts` Fetch wrapper injecting `Authorization: Bearer <token>` header on every request
- [X] T010 Create `frontend-prototype/src/lib/query-client.tsx` QueryClientProvider with default retry and error handling; wire AuthProvider + QueryClientProvider into `frontend-prototype/src/app/layout.tsx`
- [X] T011 [US1] Create `frontend-prototype/src/app/login/page.tsx` with email + password form calling POST `/auth/token/`; redirect to `/health` on success; display backend error on failure
- [X] T012 [US1] Create `frontend-prototype/src/app/(protected)/layout.tsx` with sidebar navigation to 6 modules + header with user info and logout
- [X] T013 [US1] Create `frontend-prototype/src/components/jwt-claims.tsx` decoding JWT and displaying tenant_id, user_id, email, exp
- [X] T014 [US1] Add profile, refresh, verify, change password, logout operations in auth page (GET `/auth/users/me/`, POST `/auth/token/refresh/`, POST `/auth/token/verify/`, POST `/auth/users/me/change-password/`, POST `/auth/logout/`)

---

## Phase 3: Shared UI Components (6 tasks)

Build reusable components used by all modules — **BLOCKS all module page work**.

**Validation Gate**: DataTable shows "Load More", CrudForm displays field errors, RawJsonToggle shows/hides JSON.

- [X] T015 [P] Create `frontend-prototype/src/components/data-table.tsx` generic table with columns config, "Load More" button for cursor pagination
- [X] T016 [P] Create `frontend-prototype/src/components/crud-form.tsx` generic form displaying field-level validation errors and supporting create/edit modes; also create `frontend-prototype/src/components/confirm-dialog.tsx` for delete confirmation
- [X] T017 [P] Create `frontend-prototype/src/components/raw-json-toggle.tsx` collapsible showing raw JSON responses with syntax formatting
- [X] T018 [P] Create `frontend-prototype/src/components/error-boundary.tsx` React error boundary catching and displaying error details
- [X] T019 [P] Create `frontend-prototype/src/components/status-badge.tsx` color-coded badge for entity states
- [X] T020 [P] Create `frontend-prototype/src/hooks/use-crud.ts` and `frontend-prototype/src/hooks/use-pagination.ts` for TanStack Query integration

---

## Phase 4: Health Module (2 tasks)

Implement the simplest module — validates backend connectivity.

**Validation Gate**: Health page shows green badge when backend running, red when unreachable; response time displays.

- [X] T021 [US2] Create `frontend-prototype/src/app/(protected)/health/page.tsx` calling GET `/health/`, displaying StatusBadge and response time
- [X] T022 [US2] [P] Add RawJsonToggle showing full health check JSON response

---

## Phase 5: Auth Admin Module (3 tasks)

Implement Users, Branches, and Roles management tabs.

**Validation Gate**: All three tabs render with data; Users and Roles support CRUD; Branches read-only.

- [X] T023 [US1] Create Users tab in `frontend-prototype/src/app/(protected)/auth-admin/page.tsx` with CRUD for GET/POST `/auth/users/`, GET/PUT/DELETE `/auth/users/{id}/`
- [X] T024 [US1] [P] Create Branches tab with read-only list and detail view; GET `/auth/branches/`, GET `/auth/branches/{id}/`
- [X] T025 [US1] [P] Create Roles tab with CRUD for GET/POST `/auth/roles/`, GET/PUT/DELETE `/auth/roles/{id}/`

---

## Phase 6: Inventory Module (6 tasks)

Implement products, categories, suppliers, stock movements, price lists, and history — **largest module with 19 endpoints**.

**Validation Gate**: All 19 inventario endpoints exercisable; search works; stock movements immutable; category tree renders.

- [X] T026 [US3] Create Products tab in `frontend-prototype/src/app/(protected)/inventario/page.tsx` with CRUD and search; endpoints: GET/POST `/products/`, GET/PUT/DELETE `/products/{id}/`, GET `/products/{id}/stock/`, POST `/products/search/`
- [X] T027 [US3] [P] Create Categories tab with tree view and optional parent_id nesting; GET/POST `/categories/`, GET/PUT/DELETE `/categories/{id}/`, GET `/categories/tree/`
- [X] T028 [US3] [P] Create Suppliers tab with search; GET/POST `/suppliers/`, GET/PUT/DELETE `/suppliers/{id}/`, GET `/suppliers/search/`
- [X] T029 [US3] [P] Create Stock Movements tab with create-only form (no edit/delete); GET/POST `/movements/`, GET `/movements/{id}/`
- [X] T030 [US3] [P] Create Price Lists tab with CRUD and "Set as default" action; GET/POST `/price-lists/`, GET/PUT/DELETE `/price-lists/{id}/`, POST `/price-lists/{id}/set_default/`
- [X] T031 [US3] [P] Create Price History and Cost History tabs (read-only); GET `/price-history/`, GET `/price-history/{id}/`, GET `/cost-history/`, GET `/cost-history/{id}/`

---

## Phase 7: Sales Module (4 tasks)

Implement customers, sale orders with nested items, status transitions, and invoice linking.

**Validation Gate**: Customer CRUD works; Orders show status badges; Items nest within order detail; Confirm/Authorize change status.

- [X] T032 [US4] Create Customers tab in `frontend-prototype/src/app/(protected)/ventas/page.tsx` with CRUD; GET/POST `/ventas/customers/`, GET/PUT/DELETE `/ventas/customers/{id}/`
- [X] T033 [US4] [P] Create Sale Orders tab with CRUD and status badges; GET/POST `/ventas/orders/`, GET/PUT/DELETE `/ventas/orders/{id}/`
- [X] T034 [US4] [P] Create nested Order Items in order detail view with add/edit/delete; GET/POST `/ventas/orders/{id}/items/`, GET/PATCH/DELETE `/ventas/orders/{id}/items/{item_id}/`
- [X] T035 [US4] [P] Add "Confirm" and "Authorize" status transition buttons and invoice link display; POST `/ventas/orders/{id}/confirm/`, POST `/ventas/orders/{id}/authorize/`, GET `/ventas/orders/{id}/invoice/`

---

## Phase 8: Invoicing Module (4 tasks)

Implement ARCA credential management, comprobante emission, CAE authorization, QR display, and CAEA lifecycle — **13 facturacion endpoints**.

**Validation Gate**: Comprobante emit form works; CAEA request and sin-movimiento actions work; QR displays for authorized comprobantes; ARCA errors shown.

- [X] T036 [US5] Create Credentials and Puntos de Venta tabs in `frontend-prototype/src/app/(protected)/facturacion/page.tsx` with CRUD; GET/POST/PUT/DELETE `/facturacion/credentials/` and `/facturacion/puntos-de-venta/`
- [X] T037 [US5] [P] Create Comprobantes tab with DataTable, emit form, and read-only detail; GET `/facturacion/comprobantes/`, POST `/facturacion/comprobantes/emitir/`, GET `/facturacion/comprobantes/{id}/`
- [X] T038 [US5] Add "Authorize" action button and QR display on comprobante detail; POST `/facturacion/comprobantes/{id}/authorize/`, GET `/facturacion/comprobantes/{id}/qr/`
- [X] T039 [US5] [P] Create CAEA tab with listing, detail, "Request CAEA" and "Sin Movimiento" actions; GET `/facturacion/caeas/`, GET `/facturacion/caeas/{id}/`, POST `/facturacion/caeas/solicitar/`, POST `/facturacion/caeas/{id}/sin-movimiento/`

---

## Phase 9: Sync Module (3 tasks)

Implement sync session management, push/pull operations, and device status checking — **5 sync endpoints**.

**Validation Gate**: All 5 sync endpoints exercisable; Push/pull payloads visible; Device status returns data.

- [X] T040 [US6] Create Sync Sessions tab in `frontend-prototype/src/app/(protected)/sync/page.tsx` with create/delete session; GET/POST `/sync/sessions/`, GET/DELETE `/sync/sessions/{id}/`
- [X] T041 [US6] Add "Push" and "Pull" action buttons with request/response payload display; POST `/sync/push/`, POST `/sync/pull/`
- [X] T042 [US6] [P] Add Device Status check with device_id input and "Check Status" button; GET `/sync/status/{device_id}/`

---

## Phase 10: Integration & Hardening (4 tasks)

Implement automatic token refresh, global error handling, Docker validation, and endpoint coverage verification.

**Validation Gate**: Token refresh works transparently; Docker image <200MB, builds <60s; All 62 endpoints confirmed accessible.

- [X] T043 Implement 401 interceptor with automatic token refresh in `frontend-prototype/src/lib/api-client.ts`
- [X] T044 Add global error boundary wrapping app in `frontend-prototype/src/app/layout.tsx`
- [X] T045 [P] Docker compose end-to-end validation — build image (<200MB, <60s), start full stack, verify frontend→backend connectivity
- [X] T046 [P] Endpoint coverage walkthrough — verify all 62 endpoints exercisable through UI, update `specs/012-prototype-frontend-prototype/quickstart.md`

---

## Task Summary by Phase

| Phase | Name | Tasks | Cumulative |
|-------|------|-------|------------|
| 1 | Project Scaffolding | 7 | 7 |
| 2 | Auth & Layout | 7 | 14 |
| 3 | Shared Components | 6 | 20 |
| 4 | Health Module | 2 | 22 |
| 5 | Auth Admin | 3 | 25 |
| 6 | Inventory | 6 | 31 |
| 7 | Sales | 4 | 35 |
| 8 | Invoicing | 4 | 39 |
| 9 | Sync | 3 | 42 |
| 10 | Integration | 4 | **46** |

---

## Parallelization Opportunities

**After Phase 3 (foundation complete)**: Phases 4-9 (all module pages) execute in parallel.

Within each module:
- **US1 Auth Admin**: T023 + T024 + T025 parallel
- **US3 Inventory**: T026-T031 all parallel
- **US4 Sales**: T032 + T033 parallel
- **US5 Invoicing**: T036 + T037 + T039 parallel
- **US6 Sync**: T040 + T042 parallel

**Optimal multi-agent execution**:
- Sequential: Phases 1-3 (20 tasks, ~2-3 hours)
- Parallel: Phases 4-9 (22 tasks, 3 agents × ~7 tasks each, ~1.5 hours)
- Sequential: Phase 10 (4 tasks, ~30 minutes)
- **Total wall time**: ~4-5 hours with 3 agents

---

## Implementation Strategy

**MVP First** (US1 + US2):
1. Phases 1-3: Foundation (T001-T020)
2. Phase 4: Health Module (T021-T022)
3. **Gate**: Login works, health page displays, JWT claims visible

**Incremental Delivery**:
1. Foundation → Auth + Health (MVP)
2. Add Inventory (largest module)
3. Add Sales (order lifecycle)
4. Add Invoicing (ARCA workflows)
5. Add Sync (remaining endpoints)
6. Polish & integration

**All 22 FRs covered**; No test framework needed (prototype IS the testing tool)
