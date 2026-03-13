# E2E Test Scenario Matrix

> **Canonical test scenario source** for feature 013-e2e-frontend-testing.
> Auto-derived from OpenAPI specs (`api/openapi/*.yaml`) and frontend-prototype tab components.
>
> **Source of truth**: This document. OpenAPI specs are the authoritative API reference;
> this document bridges them to Playwright-actionable UI scenarios.
>
> **Generated**: 2026-02-18

---

## Conventions

- **Scenario IDs**: `{MODULE_PREFIX}-{NNN}` (e.g., `H-001`, `AU-001`, `INV-001`)
- **Preconditions**: What seed data or prior steps are required
- **Steps**: Playwright UI actions (click, fill, verify) — NOT raw API calls
- **Expected**: What the TESTER agent should verify after each step
- **API Exercised**: Which backend endpoints are hit (for BACKEND-EXPERT correlation)
- **Severity if fails**: CRITICAL / HIGH / MEDIUM / LOW

### Module Prefixes

| Prefix | Module | Frontend Route | Tabs |
|--------|--------|----------------|------|
| `H` | Health | `/health` | (none — single page) |
| `AU` | Auth Admin | `/auth-admin` | Users, Roles, Branches, Operations |
| `INV` | Inventario | `/inventario` | Products, Categories, Suppliers, Price Lists, Movements, History |
| `VEN` | Ventas | `/ventas` | Customers, Orders |
| `FAC` | Facturacion | `/facturacion` | Comprobantes, Credentials, Puntos de Venta, CAEA |
| `SYN` | Sync | `/sync` | Sessions, Status, Operations |
| `E2E` | Cross-Module | (multiple routes) | End-to-end workflows |

### Seed Data Available

All scenarios assume `seed_all` has been executed. Key seeded entities:

| Entity | Approx. Count | Key Examples |
|--------|---------------|--------------|
| Users | 4 | admin@gravitea-demo.com (Admin), vendedor@gravitea-demo.com (Vendedor), gerente@gravitea-demo.com (Gerente), deposito@gravitea-demo.com (Deposito) |
| Roles | 4 | Administrador, Vendedor, Gerente, Deposito |
| Branches | 2 | Sucursal Centro, Sucursal Norte |
| Products | ~10 | Various SKUs with categories and suppliers |
| Categories | ~5 | Hierarchical (parent/child) |
| Suppliers | ~3 | With tax_id, email, contact |
| Price Lists | ~2 | One default, one custom |
| Movements | ~26 | SALE, PURCHASE, ADJ types |
| Customers | ~3 | With CUIT, razon_social, condicion_iva |
| Orders | ~3 | DRAFT, CONFIRMED, INVOICED statuses |
| Comprobantes | ~5 | DRAFT status, various cbte_tipo (Factura A/B/C) |
| ARCA Credentials | 1 | Homologacion environment |
| Puntos de Venta | 3 | Electronic tipo |
| CAEA | 1 | ACTIVE status |

### Login Credentials

| User | Email | Password | Role |
|------|-------|----------|------|
| Admin | admin@gravitea-demo.com | admin123 | Administrador |
| Vendedor | vendedor@gravitea-demo.com | vendedor123 | Vendedor |
| Gerente | gerente@gravitea-demo.com | gerente123 | Gerente |
| Deposito | deposito@gravitea-demo.com | deposito123 | Deposito |

---

## Module: Health (H)

**Route**: `/health` | **API**: `GET /api/v1/health/`

| ID | Scenario | Steps | Expected | Severity |
|----|----------|-------|----------|----------|
| H-001 | Health page loads and shows healthy status | Navigate to Health via sidebar. Read overall status badge. | Status shows "healthy". Database, Cache, Migrations sub-checks all show green/healthy. Version and timestamp displayed. | CRITICAL |
| H-002 | Health sub-checks display latency | On health page, inspect individual check cards. | Database latency_ms and Cache latency_ms are numeric values > 0. Migrations pending = 0. | MEDIUM |
| H-003 | Health page auto-refreshes | Wait 30+ seconds on health page. Observe timestamp change. | Timestamp updates without manual page reload. | LOW |

**Total**: 3 scenarios

---

## Module: Auth Admin (AU)

**Route**: `/auth-admin`

### Tab: Users (`AU-01x`)

**API**: `GET /api/v1/auth/users/` | **Component**: `users-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| AU-001 | Users tab loads seeded users | Logged in as admin | Click "Users" tab. Wait for table to load. | Table shows seeded users (admin, vendedor, gerente, deposito). Columns: email, full_name, is_active, role name, default branch name. | CRITICAL |
| AU-002 | Users pagination works | >1 page of users | Scroll to bottom or click "Load More". | Additional users load. No duplicates. | MEDIUM |
| AU-003 | User row shows nested role/branch | Logged in as admin | Inspect any user row. | Role column shows role name (e.g., "Administrador"), not UUID. Branch column shows branch name, not UUID. | HIGH |

### Tab: Roles (`AU-02x`)

**API**: `GET/POST/PATCH/DELETE /api/v1/auth/roles/` | **Component**: `roles-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| AU-010 | Roles tab loads seeded roles | Logged in as admin | Click "Roles" tab. Wait for table. | Table shows seeded roles (Administrador, Vendedor, Gerente, Deposito). Shows name and permissions. | CRITICAL |
| AU-011 | Create new role | Logged in as admin | Click create button. Fill name="TestRole", permissions="users.view,sales.view". Submit. | New role appears in table. Name and permissions match input. | HIGH |
| AU-012 | Edit existing role | AU-011 completed | Click edit on "TestRole". Change name to "TestRoleEdited". Save. | Role name updated in table. | HIGH |
| AU-013 | Delete role (no users assigned) | AU-012 completed | Click delete on "TestRoleEdited". Confirm deletion. | Role disappears from table. No error. | HIGH |
| AU-014 | Delete role with assigned users fails | Seeded roles | Attempt to delete "Vendedor" role (has users). | Error message: role cannot be deleted because users are assigned. | MEDIUM |

### Tab: Branches (`AU-03x`)

**API**: `GET /api/v1/auth/branches/` | **Component**: `branches-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| AU-020 | Branches tab loads seeded branches | Logged in as admin | Click "Branches" tab. Wait for table. | Table shows Sucursal Centro and Sucursal Norte. Columns: name, address, is_active, created_at. | CRITICAL |
| AU-021 | Branches are read-only | Logged in as admin | Inspect branches tab for create/edit/delete buttons. | No create, edit, or delete buttons present (read-only). | LOW |

### Tab: Operations (`AU-04x`)

**API**: Multiple auth endpoints | **Component**: `operations-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| AU-030 | Get current user profile (/me) | Logged in as admin | Click "Operations" tab. Trigger "Get Profile" action. | Shows current user's email, full_name, role, branch, permissions. | HIGH |
| AU-031 | Refresh JWT token | Logged in as admin | Trigger "Refresh Token" action. | New access token received. No logout occurs. Session continues. | HIGH |
| AU-032 | Verify JWT token | Logged in as admin | Trigger "Verify Token" action. | Token verified successfully (200 response). | MEDIUM |
| AU-033 | Change password | Logged in as admin | Fill current_password="admin123", new_password="admin456". Submit. | Success message. Can still operate (or re-login with new password). | HIGH |
| AU-034 | Change password with wrong current | Logged in as admin | Fill current_password="wrongpass", new_password="admin456". Submit. | Error message about incorrect current password. | MEDIUM |
| AU-035 | Logout | Logged in as admin | Trigger "Logout" action. | Redirected to login page. Cannot access protected routes. | CRITICAL |

**Auth Admin Total**: 16 scenarios

---

## Module: Inventario (INV)

**Route**: `/inventario`

### Tab: Products (`INV-01x`)

**API**: `GET/POST /api/v1/products/` | **Component**: `products-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-001 | Products tab loads seeded products | Logged in as admin | Click "Products" tab. Wait for table. | Table shows seeded products. Columns: sku, name, category_name, supplier_name, cost_price, is_active. | CRITICAL |
| INV-002 | Products pagination | Seeded products | Click "Load More" if available. | More products load without duplicates. | MEDIUM |
| INV-003 | Create new product | Logged in as admin | Click create button. Fill sku="TEST-001", name="Test Product", cost_price="100.50". Submit. | New product appears in table with correct fields. | HIGH |
| INV-004 | Product shows category and supplier names | Seeded products | Inspect product rows. | Category and supplier show human-readable names, not UUIDs. | HIGH |

### Tab: Categories (`INV-02x`)

**API**: `GET /api/v1/categories/tree/`, `POST /api/v1/categories/` | **Component**: `categories-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-010 | Categories tree loads | Logged in as admin | Click "Categories" tab. | Hierarchical tree displays seeded categories (parent/child relationships visible). | CRITICAL |
| INV-011 | Create root category | Logged in as admin | Click create. Fill name="New Root Category". Submit (no parent). | New root category appears in tree. | HIGH |
| INV-012 | Create child category | INV-011 completed | Click create. Fill name="Child Category", parent=UUID of "New Root Category". Submit. | Child appears nested under parent in tree. | HIGH |

### Tab: Suppliers (`INV-03x`)

**API**: `GET /api/v1/suppliers/`, `GET /api/v1/suppliers/search/`, `POST /api/v1/suppliers/` | **Component**: `suppliers-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-020 | Suppliers tab loads | Logged in as admin | Click "Suppliers" tab. | Table shows seeded suppliers with name, tax_id, email, contact_info, address. | CRITICAL |
| INV-021 | Search suppliers | Seeded suppliers | Type a known supplier name in search box. | Table filters to matching suppliers via search endpoint. | HIGH |
| INV-022 | Create supplier | Logged in as admin | Click create. Fill name="Test Supplier", tax_id="20-12345678-9", email="test@supplier.com". Submit. | New supplier appears in table. | HIGH |
| INV-023 | Search returns no results | Seeded suppliers | Type "zzzznonexistent" in search box. | Empty state or "No results" message. No error. | LOW |

### Tab: Price Lists (`INV-04x`)

**API**: `GET/POST/PATCH/DELETE /api/v1/price-lists/`, `POST .../set_default/` | **Component**: `price-lists-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-030 | Price lists load | Logged in as admin | Click "Price Lists" tab. | Table shows seeded price lists with name, margin_pct. One marked as default. | CRITICAL |
| INV-031 | Create price list | Logged in as admin | Click create. Fill name="Holiday Prices", margin_pct="25". Submit. | New price list appears in table. | HIGH |
| INV-032 | Edit price list | INV-031 completed | Click edit on "Holiday Prices". Change margin_pct to "30". Save. | Margin updated in table. | HIGH |
| INV-033 | Set default price list | INV-031 completed | Click "Set Default" on "Holiday Prices". | "Holiday Prices" becomes default. Previous default loses default status. | HIGH |
| INV-034 | Delete price list | INV-031 completed | Click delete on "Holiday Prices". Confirm. | Price list removed from table. | MEDIUM |

### Tab: Movements (`INV-05x`)

**API**: `GET/POST /api/v1/movements/` | **Component**: `movements-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-040 | Movements tab loads seeded movements | Logged in as admin | Click "Movements" tab. | Table shows seeded movements. Columns: product_sku, product_name, branch_name, type, quantity_delta, created_at. | CRITICAL |
| INV-041 | Record new movement | Seeded products/branches | Click create. Select product, branch, type="PURCHASE", qty="10". Submit. | New movement appears in table with correct fields. quantity_delta shows positive value. | HIGH |
| INV-042 | Movements are immutable | Seeded movements | Inspect movements tab for edit/delete buttons. | No edit or delete buttons (append-only ledger). | MEDIUM |
| INV-043 | Movement pagination | Seeded movements | Click "Load More" if available. | More movements load. Ordered by created_at descending. | MEDIUM |

### Tab: History (`INV-06x`)

**API**: `GET /api/v1/price-history/`, `GET /api/v1/cost-history/` | **Component**: `history-tabs.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| INV-050 | Price history loads | Logged in as admin | Click "History" tab, select "Price History" sub-tab. | Table shows price history entries: product_sku, price_list_name, price, valid_from, valid_to. | HIGH |
| INV-051 | Cost history loads | Logged in as admin | Click "History" tab, select "Cost History" sub-tab. | Table shows cost history entries: product_sku, cost, valid_from, valid_to. | HIGH |
| INV-052 | History is read-only | Logged in as admin | Inspect history tabs for create/edit/delete. | No mutation buttons (read-only audit trail). | LOW |

**Inventario Total**: 20 scenarios

---

## Module: Ventas (VEN)

**Route**: `/ventas`

### Tab: Customers (`VEN-01x`)

**API**: `GET/POST /api/v1/ventas/customers/` | **Component**: `customers-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| VEN-001 | Customers tab loads | Logged in as admin | Click "Customers" tab. | Table shows seeded customers: cuit, razon_social, condicion_iva_display, email, is_active. | CRITICAL |
| VEN-002 | Create customer | Logged in as admin | Click create. Fill cuit="20-33344455-6", razon_social="Test Customer SRL", doc_tipo, condicion_iva, domicilio, email. Submit. | New customer appears with correct Argentine-specific fields. | HIGH |
| VEN-003 | Customer condicion_iva displays label | Seeded customers | Inspect customer rows. | condicion_iva shows human-readable label (e.g., "Responsable Inscripto"), not raw code. | MEDIUM |

### Tab: Orders (`VEN-02x`)

**API**: Multiple `/api/v1/ventas/orders/` endpoints | **Component**: `orders-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| VEN-010 | Orders tab loads seeded orders | Logged in as admin | Click "Orders" tab. | Table shows seeded orders: customer_name, branch_name, status, total_amount, sale_date. | CRITICAL |
| VEN-011 | Create new order | Seeded customers/branches | Click create. Select customer and branch. Submit. | New DRAFT order appears in table. | HIGH |
| VEN-012 | View order detail | Seeded orders | Click on an order row. | Expandable detail panel shows: customer, branch, status, items list, amounts. | HIGH |
| VEN-013 | Add item to DRAFT order | VEN-011 completed | In order detail, click "Add Item". Select product, fill quantity, unit_price, tax_rate. Submit. | Item appears in order items list. Total recalculated. | HIGH |
| VEN-014 | Confirm DRAFT order | VEN-013 completed | Click "Confirm" button on DRAFT order. | Order status changes from DRAFT to CONFIRMED. Confirm button disappears. | CRITICAL |
| VEN-015 | Invoice CONFIRMED order | VEN-014 completed | Click "Invoice" button on CONFIRMED order. | Order status changes to INVOICED. Comprobante ID appears. Invoice button disappears. | CRITICAL |
| VEN-016 | Cannot confirm already-confirmed order | CONFIRMED order | Inspect CONFIRMED order actions. | "Confirm" button not present. Only "Invoice" available. | MEDIUM |
| VEN-017 | Order total computation | Order with items | Inspect order detail amounts. | subtotal + iva_amount computed at render time. Total matches sum. | HIGH |

**Ventas Total**: 11 scenarios

---

## Module: Facturacion (FAC)

**Route**: `/facturacion`

### Tab: Comprobantes (`FAC-01x`)

**API**: `GET /api/v1/facturacion/comprobantes/`, `POST .../authorize/` | **Component**: `comprobantes-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| FAC-001 | Comprobantes tab loads | Logged in as admin | Click "Comprobantes" tab. | Table shows comprobantes: cbte_tipo label (e.g., "Factura A"), punto_venta_numero, cbte_nro, customer_name, imp_total, status, cae, cbte_fch. | CRITICAL |
| FAC-002 | Comprobante type shows label | Seeded comprobantes | Inspect cbte_tipo column. | Shows "Factura A" / "Factura B" / "Factura C" etc., not numeric codes (1, 6, 11). | HIGH |
| FAC-003 | Comprobante detail panel | Seeded comprobantes | Click on a comprobante row. | Detail shows: customer, doc type, emitter CUIT, date, neto/iva/tributos/total amounts, CAE info, QR link. | HIGH |
| FAC-004 | Customer name fallback | Comprobante with null customer_name | Inspect comprobante with no customer_name. | Falls back to "Doc {doc_tipo}-{doc_nro}" format. | MEDIUM |
| FAC-005 | Authorize DRAFT comprobante | DRAFT comprobante exists, ARCA credentials configured | Click "Authorize" on DRAFT comprobante. | Status changes (to VALIDANDO → AUTORIZADO or RECHAZADO depending on ARCA). CAE assigned if authorized. | CRITICAL |
| FAC-006 | ARCA error display | Failed authorization | After failed authorize attempt. | ARCA error details shown in detail panel (observaciones/errores). | HIGH |
| FAC-007 | Comprobante status badges | Various statuses | Inspect status column. | DRAFT, VALIDANDO, AUTORIZADO, OBSERVADO, RECHAZADO each show distinct visual badge. | MEDIUM |

### Tab: Credentials (`FAC-02x`)

**API**: `GET/POST /api/v1/facturacion/credentials/` | **Component**: `credentials-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| FAC-010 | Credentials tab loads | Logged in as admin | Click "Credentials" tab. | Table shows ARCA credentials: cuit_holder, cuit_represented, is_production, is_active, certificate_expires_at. | CRITICAL |
| FAC-011 | Create credential | Logged in as admin | Click create. Fill cuit_holder, certificate_pem, private_key_pem, select environment. Submit. | New credential appears in table. | HIGH |
| FAC-012 | Production/Homologacion display | Seeded credentials | Inspect is_production column. | Shows "Production" or "Homologacion" label, not boolean. | MEDIUM |

### Tab: Puntos de Venta (`FAC-03x`)

**API**: `GET/POST /api/v1/facturacion/puntos-de-venta/` | **Component**: `puntos-venta-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| FAC-020 | Puntos de venta tab loads | Logged in as admin | Click "Puntos de Venta" tab. | Table shows: numero, tipo, description, is_active, fecha_alta. | CRITICAL |
| FAC-021 | Create punto de venta | Logged in as admin | Click create. Fill numero, tipo (electronic/manual), description. Submit. | New punto de venta appears in table. | HIGH |

### Tab: CAEA (`FAC-04x`)

**API**: `GET /api/v1/facturacion/caeas/`, `POST .../solicitar/`, `POST .../{id}/sin-movimiento/` | **Component**: `caea-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| FAC-030 | CAEA tab loads | Logged in as admin | Click "CAEA" tab. | Table shows CAEAs: punto_venta_numero, caea_code, periodo, orden, vigencia dates, status. | CRITICAL |
| FAC-031 | Solicitar CAEA | Punto de venta exists, ARCA credentials | Click "Solicitar". Select punto_venta, fill periodo (YYYYMM), orden (1st/2nd quincena). Submit. | New CAEA appears with status ACTIVE and assigned caea_code. | HIGH |
| FAC-032 | Report CAEA sin movimiento | ACTIVE CAEA exists | Click "Sin Movimiento" button on ACTIVE CAEA. | CAEA status changes to REPORTED_NO_MOVEMENT. Sin Movimiento button disappears. | HIGH |
| FAC-033 | Sin Movimiento button visibility | Various CAEA statuses | Inspect CAEA rows. | "Sin Movimiento" button only appears for ACTIVE status. Not on REPORTED, EXPIRED, etc. | MEDIUM |

**Facturacion Total**: 17 scenarios

---

## Module: Sync (SYN)

**Route**: `/sync`

### Tab: Sessions (`SYN-01x`)

**API**: `GET/POST/DELETE /api/v1/sync/sessions/` | **Component**: `sessions-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| SYN-001 | Sessions tab loads | Logged in as admin | Click "Sessions" tab. | Table shows sync sessions: device_id, status, last_sync_at, pending_operations, conflicts, created_at. | CRITICAL |
| SYN-002 | Register new device | Logged in as admin | Click create. Fill device_id="test-device-001", select branch. Submit. | New session appears in table with status. | HIGH |
| SYN-003 | Unregister device | SYN-002 completed | Click "Unregister" on test-device-001. Confirm. | Device session removed from table. | HIGH |

### Tab: Status (`SYN-02x`)

**API**: `GET /api/v1/sync/status/{device_id}/` | **Component**: `status-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| SYN-010 | Query device status | Registered device exists | Click "Status" tab. Enter device_id. Press Enter. | Shows: device_id, status, last_sync_at, pending_operations, conflicts, sync_vector. | HIGH |
| SYN-011 | Query non-existent device | No device with given ID | Enter "nonexistent-device-xyz". Press Enter. | Error message or empty state. No crash. | MEDIUM |
| SYN-012 | Status detail expansion | SYN-010 completed | Click on status result to expand. | Detail panel shows full sync_vector and additional metadata. | LOW |

### Tab: Operations (`SYN-03x`)

**API**: `POST /api/v1/sync/pull/`, `POST /api/v1/sync/push/` | **Component**: `operations-tab.tsx`

| ID | Scenario | Preconditions | Steps | Expected | Severity |
|----|----------|---------------|-------|----------|----------|
| SYN-020 | Pull changes | Registered device | In Operations tab, fill device_id. Click "Pull". | Response shows: changes array, server_timestamp, has_more flag. | HIGH |
| SYN-021 | Pull with entity filter | Registered device | Fill device_id, entity_types="products,categories". Click "Pull". | Only product and category changes returned. | MEDIUM |
| SYN-022 | Push changes | Registered device | Fill device_id, enter operations JSON array. Click "Push". | Response shows: status, created count, skipped count, errors array, server_timestamp. | HIGH |
| SYN-023 | Push with invalid JSON | Registered device | Fill device_id, enter malformed JSON. Click "Push". | Validation error message. No crash. | MEDIUM |

**Sync Total**: 10 scenarios

---

## Cross-Module Workflows (E2E)

These scenarios span multiple modules and test the integration between them.

### E2E-001: Sale-to-Invoice Full Workflow

**Severity**: CRITICAL

| Step | Module | Action | Expected |
|------|--------|--------|----------|
| 1 | Auth | Login as admin | Dashboard loads |
| 2 | Ventas | Navigate to Ventas > Customers tab | Customers table visible |
| 3 | Ventas | Create new customer (fill Argentine fields) | Customer appears in table |
| 4 | Ventas | Navigate to Orders tab | Orders table visible |
| 5 | Ventas | Create new order (select new customer + branch) | DRAFT order appears |
| 6 | Ventas | Click order row, add 2+ items (product, qty, price, tax) | Items show in detail, total recalculated |
| 7 | Ventas | Click "Confirm" on order | Status → CONFIRMED |
| 8 | Ventas | Click "Invoice" on confirmed order | Status → INVOICED, comprobante_id appears |
| 9 | Facturacion | Navigate to Facturacion > Comprobantes tab | New comprobante visible with DRAFT status |
| 10 | Facturacion | Verify comprobante amounts match order | imp_total matches order total |

### E2E-002: Credit Note Workflow

**Severity**: HIGH

| Step | Module | Action | Expected |
|------|--------|--------|----------|
| 1 | Auth | Login as admin | Dashboard loads |
| 2 | Facturacion | Navigate to Comprobantes tab | Existing comprobantes visible |
| 3 | Facturacion | Identify an AUTORIZADO comprobante | Has CAE, customer info |
| 4 | Facturacion | (If supported) Create credit note referencing original | Credit note comprobante created |
| 5 | Facturacion | Verify credit note has associated comprobante reference | CbteAsoc field populated |

**Note**: Credit note creation may depend on ARCA integration availability. If not available in frontend, document as a gap.

### E2E-003: Multi-Role Access Discovery

**Severity**: HIGH

| Step | Module | Action | Expected |
|------|--------|--------|----------|
| 1 | Auth | Login as admin (Administrador role) | Full access to all modules |
| 2 | — | Navigate through all 6 module pages | All tabs accessible, data loads |
| 3 | Auth | Logout | Redirected to login |
| 4 | Auth | Login as vendedor (Vendedor role) | Dashboard loads |
| 5 | — | Navigate through all 6 module pages | Document which tabs load vs. show errors/empty |
| 6 | Auth | Logout | Redirected to login |
| 7 | Auth | Login as gerente (Gerente role) | Dashboard loads |
| 8 | — | Navigate through all 6 module pages | Document which tabs load vs. show errors/empty |
| 9 | Auth | Logout | Redirected to login |
| 10 | Auth | Login as deposito (Deposito role) | Dashboard loads |
| 11 | — | Navigate through all 6 module pages | Document which tabs load vs. show errors/empty |
| 12 | — | Compile role-permission matrix from observations | Matrix: role x module x tab → accessible/restricted |

**Cross-Module Total**: 3 workflows

---

## Scenario Summary

| Module | Prefix | Scenario Count |
|--------|--------|---------------|
| Health | H | 3 |
| Auth Admin | AU | 16 |
| Inventario | INV | 20 |
| Ventas | VEN | 11 |
| Facturacion | FAC | 17 |
| Sync | SYN | 10 |
| Cross-Module | E2E | 3 |
| **Total** | | **80** |

### By Severity

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 15 | Core module loading + key state transitions |
| HIGH | 38 | CRUD operations + important verifications |
| MEDIUM | 19 | Pagination, formatting, secondary features |
| LOW | 8 | Auto-refresh, read-only checks, detail expansions |

---

## ARCA Integration Notes

Scenarios FAC-005, FAC-006, FAC-031, FAC-032 require ARCA (Argentina's tax authority) integration. During E2E testing:

- **If ARCA homologacion is available**: Execute these scenarios against the test environment
- **If ARCA is unavailable**: Document as "ARCA-DEPENDENT — skipped" and verify the UI handles the error gracefully (error messages, timeout handling)
- **ARCA-EXPERT agent** should be consulted for any ARCA-specific failures

## Frontend Navigation Rules

Due to JWT in-memory auth (React Context):
- **NEVER** use `page.goto()` for protected routes — this clears auth context
- **ALWAYS** navigate via sidebar link clicks after initial login
- The only direct URL navigation allowed is to `/login`
- After login, all navigation must be through UI interactions (sidebar clicks, tab clicks, breadcrumbs)
