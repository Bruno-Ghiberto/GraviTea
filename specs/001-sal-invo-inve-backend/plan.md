# Implementation Plan: Integrated Sales-Invoicing-Inventory Backend

**Branch**: `001-sal-invo-inve-backend` | **Date**: 2026-02-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-sal-invo-inve-backend/spec.md`

## Summary

Implement a complete sales-to-invoice-to-inventory integration for the GRAVITEA-ERP backend. This introduces a new `ventas` module (Customer, SaleOrder, SaleOrderItem) and enhances the existing `facturacion` (Comprobante gets sale_order/customer FKs) and `inventario` (StockMovement gets status/sale_order/comprobante fields) modules. A `SaleService` orchestrator provides atomic cross-module transactions: sale confirmation reserves stock and creates an invoice draft; ARCA authorization commits stock and marks the sale invoiced; rejection releases stock and allows retry. All 43 functional requirements from the spec are covered across 8 implementation phases.

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework, djangorestframework-simplejwt, zeep (SOAP), cryptography
**Storage**: PostgreSQL 18.1 with RLS, Redis 7.x for ARCA token caching
**Testing**: pytest + pytest-django (external execution pattern for token efficiency)
**Target Platform**: Linux server (Docker/GKE), development on Windows 11
**Project Type**: Web application (backend only, no frontend in this feature)
**Performance Goals**: 50 concurrent sale confirmations without overselling; ARCA authorization < 10s p90; 10,000 orders/tenant/month
**Constraints**: DECIMAL(17,3) for money, DECIMAL(16,4) for quantities; immutable ledger; strictly monotonic CbteNro; no credit notes/CAEA/exports; single-currency (ARS)
**Scale/Scope**: 3 new models, 2 enhanced models, 1 new service, ~15 new API endpoints, ~200+ new tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Ironclad Data Model | PASS | MoneyField(17,3) for all amounts; quantities DECIMAL(16,4); ON DELETE PROTECT/CASCADE per data model; CHECK constraints on status fields; append-only ledger preserved for StockMovement |
| II | Multi-Tenant Isolation (RLS) | PASS | All new models inherit TenantBoundModel; RLS policies specified in data-model.md; _validate_tenant_references() covers all FKs; three-layer defense preserved |
| III | Modular Django Architecture | PASS | New `ventas` module with clear boundaries; SaleService handles cross-module orchestration; views remain lightweight |
| IV | Application-Level Encryption | PASS | No new PII fields requiring encryption; ARCACredential.private_key already encrypted; Customer CUIT is not PII under Argentine law |
| V | Secure Authentication | PASS | All endpoints require JWT Bearer; tenant_id from token claims; IDOR prevention via _validate_tenant_references |
| VI | Fiscal Compliance (ARCA) | PASS | Reuses existing WSAA/WSFEv1 clients; adds sale-originated invoice flow; resolver_tipo_comprobante for A/B/C determination |
| VII | Offline-First | N/A | This feature targets online flow; offline CAEA mode is out of scope per constraints |
| VIII | Query Optimization | PASS | select_related on Customer/Branch FKs; prefetch_related on SaleOrder.items; composite indexes specified |
| IX | Secure Data Operations | PASS | Serializers use explicit field lists; no `fields = '__all__'`; bulk operations not needed for this feature |
| X | Test-Driven Development | PASS | Tests planned in Phase 7 with >90% coverage target; unit + integration + security + performance categories |
| XI | JWT Authentication | PASS | Uses existing JWT infrastructure; tenant_id/branch_id from claims |
| XII | Rate Limiting | N/A | No new authentication endpoints; existing rate limiting applies |
| XIII | Cursor-Based Pagination | PASS | All list endpoints use CursorPagination; ordering by -created_at; 100 default, 1000 max |
| XIV | API Documentation | PASS | All ViewSets will include drf-spectacular annotations; OpenAPI schema auto-generated |

**Result**: All applicable gates PASS. No violations to justify.

### Post-Design Re-Check

| Decision | Constitution Principle | Verdict |
|----------|-----------------------|---------|
| Limited mutability on StockMovement status | I (append-only ledger) | PASS — only RESERVED→COMMITTED/CANCELLED transitions allowed; COMMITTED/CANCELLED are fully immutable; data fields never change |
| Nullable FKs on Comprobante | I (FK constraints) | PASS — nullable for backward compatibility; validation in SaleService ensures consistency when set |
| DECIMAL(16,4) for quantities | I (DECIMAL(17,3) mandate) | PASS — constitution specifies 17,3 for *financial* amounts; quantities are physical units, 16,4 matches existing inventario patterns |
| Customer in ventas (not core) | III (modular architecture) | PASS — sales domain entity per constitution module boundaries |

## Project Structure

### Documentation (this feature)

```text
specs/001-sal-invo-inve-backend/
├── plan.md              # This file
├── spec.md              # Feature specification (43 FRs)
├── research.md          # 10 design decisions
├── data-model.md        # Entity schemas and constraints
├── quickstart.md        # Implementation quick-start guide
├── contracts/
│   └── api-contract.md  # REST API specification
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── ventas/                    # NEW MODULE
│   │   ├── __init__.py
│   │   ├── apps.py               # app_label: gravitea_ventas
│   │   ├── models.py             # Customer, SaleOrder, SaleOrderItem
│   │   ├── serializers.py        # CustomerSerializer, SaleOrderSerializer, etc.
│   │   ├── views.py              # CustomerViewSet, SaleOrderViewSet
│   │   ├── urls.py               # /api/v1/ventas/...
│   │   ├── admin.py              # Django admin registration
│   │   ├── validators.py         # validate_cuit (Modulo-11)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── sale_service.py   # SaleService orchestrator
│   │   └── migrations/
│   │       └── 0001_initial.py
│   ├── facturacion/               # ENHANCED
│   │   └── migrations/
│   │       └── 00XX_add_sale_customer_fks.py
│   ├── inventario/                # ENHANCED
│   │   └── migrations/
│   │       └── 00XX_add_movement_status.py
│   └── core/
│       └── fields.py              # SALE_ORDER_STATUS_ENUM (if PostgresEnumField used)
├── tests/
│   ├── ventas/                    # NEW TEST MODULE
│   │   ├── __init__.py
│   │   ├── test_customer_model.py
│   │   ├── test_customer_api.py
│   │   ├── test_sale_order_model.py
│   │   ├── test_sale_order_api.py
│   │   ├── test_sale_order_item.py
│   │   ├── test_sale_service.py
│   │   ├── test_cuit_validation.py
│   │   └── test_integration.py
│   ├── facturacion/               # ENHANCED TESTS
│   │   ├── test_comprobante_sale_fk.py
│   │   └── test_invoice_from_sale.py
│   ├── inventario/                # ENHANCED TESTS
│   │   ├── test_stock_reservation.py
│   │   └── test_movement_status.py
│   └── security/                  # CROSS-MODULE SECURITY
│       └── test_sales_tenant_isolation.py
└── database/sql/
    └── ventas_rls.sql             # RLS policies for ventas tables
```

**Structure Decision**: Web application (backend only). New `ventas` module follows existing app conventions. Tests in centralized `tests/` directory per existing patterns. Service layer in `services/` subdirectory matching facturacion and inventario patterns.

---

## Phase 1: Sales Module Foundation (18 tasks)

Creates the new `ventas` Django app with Customer, SaleOrder, and SaleOrderItem models, serializers, views, and basic CRUD endpoints.

**Dependencies**: None (greenfield module)
**Covers**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-009, FR-010

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 1.1 | Create ventas app scaffold | `django-admin startapp ventas`, apps.py with `gravitea_ventas` label, register in INSTALLED_APPS | No (foundation) |
| 1.2 | Implement CUIT validator | `validators.py` with `validate_cuit()` — Modulo-11 algorithm, 11-digit format check | Yes (with 1.1) |
| 1.3 | Create Customer model | Model per data-model.md spec: cuit, doc_tipo, condicion_iva, razon_social, domicilio, email, telefono, is_active; UniqueConstraint(tenant_id, cuit); partial index on active | After 1.1 |
| 1.4 | Create SaleOrder model | Model per data-model.md: customer FK, branch FK, status (TextChoices), totals (MoneyField), confirmed_by FK, audit timestamps (sale_date, confirmed_at, invoiced_at); status transition validation in save(). NOTE: No comprobante FK — link via reverse relation `comprobante_direct` from Comprobante.sale_order | After 1.1 |
| 1.5 | Create SaleOrderItem model | Model per data-model.md: sale_order FK (CASCADE), product FK, quantity(16,4), unit_price (MoneyField), subtotal, tax_rate, iva_amount; auto-calculate in save(); parent status check | After 1.4 |
| 1.6 | Generate initial migration | `makemigrations ventas` — verify migration includes all constraints, indexes | After 1.3, 1.4, 1.5 |
| 1.7 | Create RLS policies | `database/sql/ventas_rls.sql` for Customer, SaleOrder, SaleOrderItem tables | After 1.6 |
| 1.8 | Create CustomerSerializer | DRF serializer with explicit fields, CUIT validation, condicion_iva_display read-only field | After 1.3 |
| 1.9 | Create SaleOrderSerializer | Nested customer/branch read representation, status read-only, totals read-only; create accepts customer_id, branch_id | After 1.4 |
| 1.10 | Create SaleOrderItemSerializer | product nested read, auto-calculated fields read-only; create accepts product_id, quantity, unit_price | After 1.5 |
| 1.11 | Create SaleOrderDetailSerializer | Extends SaleOrderSerializer with nested items list and comprobante info | After 1.9, 1.10 |
| 1.12 | Create CustomerViewSet | ModelViewSet with CRUD, search filter (razon_social, cuit), is_active filter, condicion_iva filter; CursorPagination | After 1.8 |
| 1.13 | Create SaleOrderViewSet | ModelViewSet (list/create/retrieve/update); status filter, customer filter, date_from/date_to filters; block PATCH for non-DRAFT | After 1.9, 1.11 |
| 1.14 | Create SaleOrderItemViewSet | Nested under SaleOrder; list/create/update/delete; block all mutations for non-DRAFT parent; duplicate product check | After 1.10 |
| 1.15 | Create URL configuration | `ventas/urls.py` with router registration; include in main `gravitea/urls.py` under `/api/v1/ventas/` | After 1.12, 1.13, 1.14 |
| 1.16 | Register Django admin | Admin classes for Customer, SaleOrder, SaleOrderItem with appropriate list_display, search, filters | After 1.3, 1.4, 1.5 |
| 1.17 | Add drf-spectacular annotations | @extend_schema decorators on all ViewSet actions; request/response examples | After 1.12, 1.13, 1.14 |
| 1.18 | Order total recalculation | Signal or method to recalculate SaleOrder.subtotal/total_iva/total_amount when items change | After 1.5 |

**Validation Gate**: Run migrations, verify all CRUD endpoints via OpenAPI schema. Customer CUIT validation rejects invalid check digits.

---

## Phase 2: Invoice Module Enhancements (10 tasks)

Adds sale_order and customer FKs to Comprobante, and emitter_condicion_iva to ARCACredential. Preserves all 334 existing tests.

**Dependencies**: Phase 1 (Customer and SaleOrder models must exist for FKs)
**Covers**: FR-017, FR-018, FR-020, FR-022

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 2.1 | Add sale_order field to Comprobante | OneToOneField to ventas.SaleOrder, null=True, blank=True, PROTECT, related_name='comprobante_direct' | No (migration dependency) |
| 2.2 | Add customer field to Comprobante | ForeignKey to ventas.Customer, null=True, blank=True, PROTECT, related_name='comprobantes' | Yes (with 2.1) |
| 2.3 | Add emitter_condicion_iva to ARCACredential | PositiveSmallIntegerField with CondicionIVA choices, default RESPONSABLE_INSCRIPTO | Yes (with 2.1) |
| 2.4 | Generate facturacion migration | `makemigrations facturacion` — verify nullable fields, no data migration needed | After 2.1, 2.2, 2.3 |
| 2.5 | Update Comprobante validation | Add validation: if sale_order is set, customer must equal sale_order.customer; prevent duplicate sale_order links | After 2.4 |
| 2.6 | Update ComprobanteSerializer | Add sale_order and customer read-only nested representations; keep backward compatible (null allowed) | After 2.5 |
| 2.7 | Create invoice-from-sale helper | Method/function to create Comprobante DRAFT from SaleOrder data: auto-determine cbte_tipo via resolver_tipo_comprobante, populate amounts from order totals, create AlicIva rows | After 2.5 |
| 2.8 | Update InvoiceService | Extend issue_comprobante to accept sale_order parameter; propagate stock commitment on success; propagate stock release on rejection; support RECHAZADO→VALIDANDO transition for retry flow | After 2.7 |
| 2.9 | Add QR endpoint for sale-originated invoices | Ensure existing QR generation works for comprobantes linked to sales | After 2.6 |
| 2.10 | Verify existing tests pass | Run all 334 existing facturacion tests — no regressions from nullable FK additions | After 2.4 |

**Validation Gate**: All 334 existing facturacion tests pass. New Comprobante can be created with and without sale_order FK.

---

## Phase 3: Inventory Module Enhancements (11 tasks)

Adds status, sale_order, and comprobante fields to StockMovement. Implements limited mutability for status transitions.

**Dependencies**: Phase 1 (SaleOrder model for FK)
**Covers**: FR-011, FR-012, FR-013, FR-014, FR-015, FR-016

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 3.1 | Create StockMovementStatus enum | TextChoices: COMMITTED, RESERVED, CANCELLED in models.py (or constants) | No (foundation) |
| 3.2 | Add status field to StockMovement | CharField with StockMovementStatus choices, default COMMITTED, db_index=True | After 3.1 |
| 3.3 | Add sale_order FK to StockMovement | ForeignKey to ventas.SaleOrder, null=True, blank=True, PROTECT | Yes (with 3.2) |
| 3.4 | Add comprobante FK to StockMovement | ForeignKey to facturacion.Comprobante, null=True, blank=True, PROTECT | Yes (with 3.2) |
| 3.5 | Generate inventario migration | `makemigrations inventario` — status defaults to COMMITTED for existing rows | After 3.2, 3.3, 3.4 |
| 3.6 | Implement limited mutability in save() | Override save() per data-model.md: allow RESERVED→COMMITTED/CANCELLED only; block all other field changes on existing records except `comprobante_id` (set during RESERVED→COMMITTED); existing immutability preserved for non-RESERVED | After 3.5 |
| 3.7 | Update available stock calculation | Modify StockSnapshot or add query method: available = physical - abs(sum(RESERVED movements)); or use existing reserved_quantity field on StockSnapshot | After 3.6 |
| 3.8 | Add movement status index | Composite index: (tenant_id, status, product_id) for efficient reservation queries | After 3.5 |
| 3.9 | Update StockService.reserve_stock() | Create StockMovement with status=RESERVED, sale_order FK, type=SALE; update StockSnapshot.reserved_quantity | After 3.6 |
| 3.10 | Add StockService.commit_reservation() | Transition RESERVED→COMMITTED movements for a sale_order; set comprobante FK; update StockSnapshot.reserved_quantity | After 3.6 |
| 3.11 | Add StockService.cancel_reservation() | Transition RESERVED→CANCELLED movements for a sale_order; update StockSnapshot.reserved_quantity; release stock | After 3.6 |

**Validation Gate**: Existing inventario tests pass. StockMovement status transitions work correctly. Available stock reflects reservations.

---

## Phase 4: Integration Layer — SaleService (14 tasks)

Implements the cross-module SaleService orchestrator with atomic transaction flows for confirmation, authorization, and rejection recovery.

**Dependencies**: Phase 1, 2, 3 (all models and service methods must exist)
**Covers**: FR-008, FR-014, FR-015, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-031, FR-032, FR-033, FR-038

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 4.1 | Create SaleService class | `apps/ventas/services/sale_service.py` — service class with dependency injection for StockService and InvoiceService | No (foundation) |
| 4.2 | Implement confirm_sale() | @transaction.atomic: validate order has items → validate stock per item (select_for_update on StockSnapshot) → reserve stock → create Comprobante DRAFT (via invoice-from-sale helper) → link to SaleOrder → set CONFIRMED + confirmed_at | After 4.1 |
| 4.3 | Implement stock validation in confirm_sale | For each SaleOrderItem: check available_quantity >= requested; raise InsufficientStockError with product details on failure; all-or-nothing (atomic) | After 4.2 |
| 4.4 | Implement invoice draft creation in confirm_sale | Call invoice-from-sale helper: determine cbte_tipo, populate amounts, create AlicIva breakdown per tax rate, set doc_tipo/doc_nro from customer | After 4.2 |
| 4.5 | Implement authorize_sale() | Call InvoiceService.issue_comprobante() with the linked comprobante → on A/O result: commit stock, set INVOICED + invoiced_at → on R result: handle rejection → on timeout: handle timeout | After 4.1 |
| 4.6 | Implement rejection handling | On Resultado R: cancel_reservation() → revert SaleOrder to CONFIRMED → revert Comprobante to RECHAZADO (already done by InvoiceService) → return error details | After 4.5 |
| 4.7 | Implement timeout handling | On timeout: InvoiceService._recover_from_timeout() → if CAE found: commit stock + INVOICED → if not found: leave CONFIRMED for retry | After 4.5 |
| 4.8 | Add confirm action to SaleOrderViewSet | `@action(detail=True, methods=['post'])` — calls SaleService.confirm_sale(); returns confirmation result with stock reservations | After 4.2 |
| 4.9 | Add authorize action to SaleOrderViewSet | `@action(detail=True, methods=['post'])` — calls SaleService.authorize_sale(); returns authorization result with CAE or error | After 4.5 |
| 4.10 | Add invoice retrieval endpoint | `@action(detail=True, methods=['get'])` on SaleOrderViewSet — returns linked comprobante or 404 | After 4.8 |
| 4.11 | Add authorize endpoint on ComprobanteViewSet | `POST /api/v1/facturacion/comprobantes/{id}/authorize/` — can also authorize directly; delegates to InvoiceService | After 4.5 |
| 4.12 | Implement IVA breakdown calculation | Calculate AlicIva rows from SaleOrderItems grouped by tax_rate; handle multiple IVA rates in single order | After 4.4 |
| 4.13 | Add CONFIRMED→DRAFT revert for retry | When authorization fails, SaleOrder reverts to CONFIRMED (not DRAFT) to preserve confirmation data; stock stays released; user can re-authorize | After 4.6 |
| 4.14 | Idempotency check on confirm/authorize | Prevent double-confirm (return current state if already CONFIRMED); prevent authorize on non-CONFIRMED; prevent authorize if already has CAE | After 4.8, 4.9 |

**Validation Gate**: Complete sale flow works: create order → add items → confirm (reserves stock, creates invoice) → authorize (gets CAE, commits stock). Rejection releases stock. Timeout recovery works.

---

## Phase 5: ARCA Authorization Integration (10 tasks)

Ensures the sale-to-invoice-to-ARCA flow works end-to-end, including CbteNro sequencing, amount mapping, and AlicIva population.

**Dependencies**: Phase 4 (SaleService must exist)
**Covers**: FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 5.1 | Map SaleOrder amounts to Comprobante | imp_total from total_amount, imp_neto from subtotal, imp_iva from total_iva; imp_trib=0 (no other taxes for now); imp_op_ex/imp_tot_conc based on customer condicion | No |
| 5.2 | Map SaleOrderItems to AlicIva rows | Group items by tax_rate → create AlicIva per group: Id from AlicIvaId enum, BaseImp=sum(subtotals), Importe=sum(iva_amounts) | After 5.1 |
| 5.3 | Set doc_tipo/doc_nro from Customer | Comprobante.doc_tipo = customer.doc_tipo, doc_nro = customer.cuit; validate doc_tipo rules per cbte_tipo (A requires CUIT) | After 5.1 |
| 5.4 | Set concepto field | Default Concepto.PRODUCTOS for product sales; allow override for service sales | After 5.1 |
| 5.5 | Verify CbteNro sequencing | Ensure InvoiceService._issue_with_transaction() correctly locks PuntoDeVenta and gets next CbteNro for sale-originated invoices | After 5.1 |
| 5.6 | Verify WSAA token caching | Ensure per-tenant WSAA tokens are cached in Redis with 11h TTL; test tenant isolation of tokens | After 5.5 |
| 5.7 | Generate fiscal QR for sale invoices | Ensure qr.py generates correct QR data including sale_order reference; QR URL format per ARCA spec | After 5.5 |
| 5.8 | Handle observed invoices (Resultado O) | CAE is granted but with warnings; commit stock normally; store observaciones; notify via response | After 5.5 |
| 5.9 | Handle multiple AlicIva rates | Support orders with items at different IVA rates (21%, 10.5%, 27%, 0%); each rate gets its own AlicIva row | After 5.2 |
| 5.10 | Amount rounding validation | Verify imp_total == imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc (ARCA rejects if not balanced); add pre-submit validation | After 5.1, 5.2 |

**Validation Gate**: Mock ARCA authorization succeeds for Type A, B, C invoices. AlicIva breakdown is correct. Amounts are balanced. CbteNro increments correctly.

---

## Phase 6: Error Handling & Recovery (8 tasks)

Implements comprehensive error handling: stock insufficient, ARCA rejection, network timeout, idempotency, and audit logging.

**Dependencies**: Phase 4, 5
**Covers**: FR-031, FR-032, FR-033, FR-034, FR-035, FR-039

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 6.1 | Standardize error responses | Ensure all error responses follow contract format: `{"error": {"code": "...", "message": "...", "details": {}}}` | No |
| 6.2 | Insufficient stock error details | Include product_id, product_sku, product_name, available, requested, branch in error response | After 6.1 |
| 6.3 | ARCA rejection error mapping | Map ARCA error codes to user-friendly messages; store raw errors in comprobante.arca_errors; return structured response | After 6.1 |
| 6.4 | Timeout recovery flow | Implement full timeout recovery: catch timeout → query FECompUltimoAutorizado → if authorized: commit + return CAE → if not: leave for retry | Yes |
| 6.5 | Certificate validation | Validate certificate expiration before attempting ARCA auth; return actionable error if expired | Yes |
| 6.6 | Audit logging for state transitions | Log all SaleOrder status transitions with timestamp, user, previous_status, new_status; store in Django's logging framework with structured JSON | After 6.1 |
| 6.7 | Cross-tenant reference blocking | Ensure 403 error with `cross_tenant_reference` code when IDOR detected via _validate_tenant_references | After 6.1 |
| 6.8 | Customer deletion protection | Return 409 with `customer_has_orders` code when deleting customer with linked SaleOrders; suggest deactivation | After 6.1 |

**Validation Gate**: All error codes from api-contract.md return correctly. Timeout recovery reconciles state. Audit logs capture all transitions.

---

## Phase 7: Testing (20 tasks)

Comprehensive test suite: unit tests, integration tests, security tests, and performance tests. All tests run externally per token efficiency protocol.

**Dependencies**: Phase 1-6 (all implementation complete)
**Covers**: SC-001 through SC-012

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 7.1 | Test fixtures: customers | Fixtures for RI, CF, Monotributo, Exento customers with valid CUITs | No (foundation) |
| 7.2 | Test fixtures: products and stock | Fixtures for products with stock at specific branches; pre-populated BranchStock | Yes (with 7.1) |
| 7.3 | Test fixtures: ARCA mocks | Mock WSFEv1Client responses: Resultado A, O, R; mock WSAA auth; mock timeout | Yes (with 7.1) |
| 7.4 | Unit: CUIT validation | Test valid CUITs, invalid check digits, wrong length, non-numeric, edge cases | After 7.1 |
| 7.5 | Unit: Customer model | Test creation, CUIT uniqueness per tenant, condicion_iva choices, is_active default | After 7.1 |
| 7.6 | Unit: SaleOrder model | Test status transitions (valid and invalid), immutability enforcement, total calculation | After 7.1 |
| 7.7 | Unit: SaleOrderItem model | Test auto-calculation (subtotal, iva_amount), parent status lock, unique product per order | After 7.1 |
| 7.8 | Unit: StockMovement status | Test RESERVED→COMMITTED, RESERVED→CANCELLED, block COMMITTED→anything, block field changes on RESERVED | After 7.2 |
| 7.9 | Integration: Customer CRUD API | Test list (with filters), create (CUIT validation), retrieve, update, delete (with protection) | After 7.4, 7.5 |
| 7.10 | Integration: SaleOrder CRUD API | Test create, list (with filters), retrieve (with nested items), update (DRAFT only), PATCH blocked for CONFIRMED | After 7.6 |
| 7.11 | Integration: SaleOrderItem API | Test add/update/delete items, auto-recalculation, duplicate product rejection, parent status lock | After 7.7 |
| 7.12 | Integration: confirm_sale flow | Test full confirmation: stock reserved, comprobante created, status=CONFIRMED, response format | After 7.2, 7.3 |
| 7.13 | Integration: authorize_sale flow | Test full authorization: mock ARCA success, stock committed, status=INVOICED, CAE stored | After 7.3 |
| 7.14 | Integration: rejection recovery | Test ARCA rejection: stock released, sale reverts to CONFIRMED, error details returned | After 7.3 |
| 7.15 | Integration: timeout recovery | Test network timeout: mock timeout then FECompConsultar; test both recovered and not-recovered paths | After 7.3 |
| 7.16 | Integration: invoice type determination | Test A (RI→RI), B (RI→CF), C (RI→Mono) invoice type auto-selection | After 7.1 |
| 7.17 | Security: tenant isolation | Test cross-tenant customer/order/item access blocked; IDOR prevention on all FKs | After 7.1 |
| 7.18 | Security: status transition enforcement | Test direct status manipulation blocked; only SaleService can transition | After 7.6 |
| 7.19 | Performance: concurrent stock reservation | ThreadPoolExecutor with 50 concurrent confirm_sale for same product; verify no overselling | After 7.2 |
| 7.20 | Regression: existing test suite | Verify all existing tests (facturacion: 334, inventario, auth, core) still pass | After 7.1 |

**Validation Gate**: >90% code coverage on ventas module. All 334 existing tests pass. Zero cross-tenant data leakage. 50 concurrent sales handled correctly.

---

## Phase 8: Docker, Migrations & Deployment (9 tasks)

Prepares the feature for deployment: Docker configuration, migration ordering, environment variables, and health checks.

**Dependencies**: Phase 7 (all tests passing)
**Covers**: Deployment readiness

### Tasks

| # | Task | Description | Parallelizable |
|---|------|-------------|----------------|
| 8.1 | Update docker-compose.yml | Add ventas module to backend service; ensure migration ordering (core → auth → inventario → facturacion → ventas) | No |
| 8.2 | Create migration dependency chain | Ensure ventas migrations depend on facturacion (for Comprobante FK) and inventario (for Product FK); verify `run_before`/`dependencies` | After 8.1 |
| 8.3 | Apply RLS policies migration | Create Django migration or management command to apply ventas_rls.sql policies | After 8.2 |
| 8.4 | Update settings | Add `gravitea_ventas` to INSTALLED_APPS; verify URL routing; add any ventas-specific settings | After 8.1 |
| 8.5 | Health check updates | Add ventas model checks to existing health check endpoint if applicable | After 8.4 |
| 8.6 | OpenAPI schema validation | Generate OpenAPI schema, validate all new endpoints are documented, verify request/response examples | After 8.4 |
| 8.7 | Create data seed script | Management command for development: create sample customers, orders, products for manual testing | After 8.4 |
| 8.8 | Update README | Add ventas module to backend README, document new endpoints and configuration | After 8.6 |
| 8.9 | Final integration smoke test | Full flow: create customer → create order → add items → confirm → authorize (mocked) → verify QR | After 8.1-8.8 |

**Validation Gate**: Docker build succeeds. All migrations apply cleanly. OpenAPI schema validates. Smoke test passes end-to-end.

---

## Task Summary

| Phase | Name | Tasks | Cumulative |
|-------|------|-------|------------|
| 1 | Sales Module Foundation | 18 | 18 |
| 2 | Invoice Module Enhancements | 10 | 28 |
| 3 | Inventory Module Enhancements | 11 | 39 |
| 4 | Integration Layer — SaleService | 14 | 53 |
| 5 | ARCA Authorization Integration | 10 | 63 |
| 6 | Error Handling & Recovery | 8 | 71 |
| 7 | Testing | 20 | 91 |
| 8 | Docker, Migrations & Deployment | 9 | 100 |
| **Total** | | **100** | |

## Parallelization Opportunities

- **Phase 1**: Tasks 1.2 can run parallel with 1.1; tasks 1.8-1.11 (serializers) parallel with 1.16 (admin)
- **Phase 2 + Phase 3**: Can execute in parallel (independent model enhancements)
- **Phase 5**: Tasks 5.4-5.9 are largely independent
- **Phase 7**: Unit tests (7.4-7.8) can run in parallel; security tests (7.17-7.18) independent from integration tests

## Integration Checkpoints

| After Phase | Checkpoint | Action |
|-------------|-----------|--------|
| Phase 1 | Ventas CRUD works | Test all endpoints via OpenAPI; verify pagination, filtering |
| Phase 3 | All model changes done | Run full existing test suite — zero regressions |
| Phase 5 | ARCA flow complete | Test with mock ARCA: A, O, R results all handled |
| Phase 7 | Full test suite | >90% coverage; all security tests pass; concurrent test pass |

## FR Coverage Matrix

| FR | Phase | Task(s) | Description |
|----|-------|---------|-------------|
| FR-001 | 1 | 1.2, 1.3 | CUIT storage and validation |
| FR-002 | 1 | 1.3 | Customer condicion_iva classification |
| FR-003 | 1 | 1.2, 1.8 | CUIT check digit validation |
| FR-004 | 4 | 4.2 | Prevent sales without valid customer |
| FR-005 | 1 | 1.4 | SaleOrder status lifecycle |
| FR-006 | 1 | 1.5 | Multiple line items |
| FR-007 | 1 | 1.18 | Auto-calculate totals |
| FR-008 | 4 | 4.3 | Stock availability validation |
| FR-009 | 1 | 1.5 | Immutable items after confirmation |
| FR-010 | 1 | 1.4 | Branch linkage |
| FR-011 | 3 | 3.9 | Stock reservation movements |
| FR-012 | 4 | 4.3 | Database-level locking |
| FR-013 | 3 | 3.7 | Available = physical - reserved |
| FR-014 | 3 | 3.10 | RESERVED→COMMITTED on authorization |
| FR-015 | 3 | 3.11 | Release stock on rejection |
| FR-016 | 3 | 3.3 | sale_order FK on movements |
| FR-017 | 4 | 4.4 | Auto-create invoice on confirmation |
| FR-018 | 4 | 4.4 | Auto-determine invoice type |
| FR-019 | 5 | 5.5 | CbteNro from FECompUltimoAutorizado |
| FR-020 | 5 | 5.1 | Amount mapping from sale |
| FR-021 | 5 | 5.2, 5.9 | IVA breakdown calculation |
| FR-022 | 2 | 2.1 | OneToOneField on Comprobante.sale_order prevents duplicates |
| FR-023 | 5 | 5.6 | WSAA tenant-specific auth |
| FR-024 | 5 | 5.6 | Token caching with 11h TTL |
| FR-025 | 5 | 5.1-5.4 | Submit with all fiscal data |
| FR-026 | 5 | 5.8 | Handle A/O/R results |
| FR-027 | 5 | 5.5 | Store CAE |
| FR-028 | 6 | 6.3 | Store errors/warnings |
| FR-029 | 5 | 5.5 | Monotonic CbteNro |
| FR-030 | 5 | 5.7 | Fiscal QR code |
| FR-031 | 4 | 4.6 | Release stock on rejection |
| FR-032 | 4 | 4.13 | Revert to CONFIRMED |
| FR-033 | 4 | 4.14 | Retry with same CbteNro |
| FR-034 | 6 | 6.4 | Timeout detection + query |
| FR-035 | 6 | 6.4 | Reconcile after timeout |
| FR-036 | 1 | 1.3, 1.4, 1.5 | TenantBoundModel inheritance |
| FR-037 | 1 | 1.3, 1.4, 1.5 | _validate_tenant_references |
| FR-038 | 4 | 4.2, 4.5 | Atomic transactions |
| FR-039 | 6 | 6.6 | Audit logging |
| FR-040 | — | existing | ARCACredential already exists |
| FR-041 | — | existing | private_key already encrypted |
| FR-042 | — | existing | environment field already exists |
| FR-043 | — | existing | per-tenant token caching exists |

## Complexity Tracking

No constitution violations to justify. All design decisions align with established principles.
