# Tasks: Integrated Sales-Invoicing-Inventory Backend

**Input**: Design documents from `/specs/001-sal-invo-inve-backend/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api-contract.md, research.md, quickstart.md
**Tests**: Included per constitution Section X (TDD mandate) and plan Phase 7

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**Testing Strategy (Constitution X — TDD)**: While test tasks are consolidated in Phase 9 for organizational clarity, implementers SHOULD follow TDD within each user story: write the relevant test from Phase 9 BEFORE or ALONGSIDE the implementation task. Phase 9 task IDs are cross-referenced in each story's checkpoint. The Phase 9 grouping enables parallel test execution and shared fixture setup.

**Deferred: ARCA Prolonged Outage Queue**: The spec edge case for exponential backoff retry queuing during ARCA outages is deferred to a future phase. Current behavior: manual retry via `authorize` endpoint. The system preserves CONFIRMED state safely during outages.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/apps/`, `backend/tests/`
- **Database**: `backend/database/sql/`
- **Config**: `backend/gravitea/settings/`, `backend/gravitea/urls.py`

---

## Phase 1: Setup (App Scaffold)

**Purpose**: Create the ventas Django app and register it in the project

- [x] T001 Create ventas app directory with `__init__.py` in `backend/apps/ventas/`
- [x] T002 Create `backend/apps/ventas/apps.py` with VentasConfig (app_label `gravitea_ventas`, verbose_name `Ventas`)
- [x] T003 [P] Add `apps.ventas` to INSTALLED_APPS in `backend/gravitea/settings/base.py`
- [x] T004 [P] Create `backend/apps/ventas/services/__init__.py` directory structure
- [x] T005 [P] Create `backend/tests/ventas/__init__.py` directory structure

**Checkpoint**: `python manage.py check` passes with ventas app registered

---

## Phase 2: Foundational (Models, Serializers, Views, URLs)

**Purpose**: All shared models, migrations, serializers, views, and URL routing that MUST be complete before user story implementation begins

**CRITICAL**: No user story work can begin until this phase is complete

### Models

- [x] T006 Implement `validate_cuit()` Modulo-11 validator in `backend/apps/ventas/validators.py` — 11-digit format check, weights [5,4,3,2,7,6,5,4,3,2], check digit computation
- [x] T007 Create Customer model in `backend/apps/ventas/models.py` per data-model.md — cuit, doc_tipo, condicion_iva, razon_social, domicilio, email, telefono, is_active; TenantBoundModel; UniqueConstraint(tenant_id, cuit); partial index on is_active
- [x] T008 Create SaleOrderStatus TextChoices and SALE_ORDER_TRANSITIONS dict in `backend/apps/ventas/models.py` — DRAFT, CONFIRMED, INVOICED with allowed transitions
- [x] T009 Create SaleOrder model in `backend/apps/ventas/models.py` per data-model.md — customer FK (PROTECT), branch FK (PROTECT), status, subtotal/total_iva/total_amount (MoneyField), confirmed_by FK (SET_NULL), audit timestamps (sale_date, confirmed_at, invoiced_at); save() enforces status transitions and immutability. NOTE: No comprobante FK here — link is via reverse relation `comprobante_direct` from Comprobante.sale_order OneToOneField
- [x] T010 Create SaleOrderItem model in `backend/apps/ventas/models.py` per data-model.md — sale_order FK (CASCADE), product FK (PROTECT), quantity(16,4), unit_price (MoneyField), subtotal, tax_rate(5,2), iva_amount; auto-calculate subtotal/iva_amount in save(); auto-populate tax_rate from product.tax_rate if not explicitly set; block edits when parent not DRAFT; UniqueConstraint(sale_order, product)
- [x] T011 Implement order total recalculation method on SaleOrder in `backend/apps/ventas/models.py` — recalculate subtotal/total_iva/total_amount from items aggregate

### Model Enhancements (Existing Modules)

- [x] T012 [P] Create StockMovementStatus TextChoices (COMMITTED, RESERVED, CANCELLED) in `backend/apps/inventario/models.py`
- [x] T013 [P] Add status field to StockMovement in `backend/apps/inventario/models.py` — CharField, StockMovementStatus choices, default COMMITTED, db_index
- [x] T014 [P] Add sale_order FK to StockMovement in `backend/apps/inventario/models.py` — ForeignKey to ventas.SaleOrder, null=True, blank=True, PROTECT
- [x] T015 [P] Add comprobante FK to StockMovement in `backend/apps/inventario/models.py` — ForeignKey to facturacion.Comprobante, null=True, blank=True, PROTECT
- [x] T016 Implement limited mutability in StockMovement.save() in `backend/apps/inventario/models.py` — allow ONLY RESERVED→COMMITTED and RESERVED→CANCELLED transitions; block all field changes on existing records except status and comprobante_id (comprobante FK is set during RESERVED→COMMITTED to link the authorizing invoice); preserve existing immutability for COMMITTED/CANCELLED
- [x] T017 Add composite index (tenant_id, status, product_id) to StockMovement in `backend/apps/inventario/models.py`
- [x] T018 [P] Add sale_order OneToOneField to Comprobante in `backend/apps/facturacion/models.py` — to ventas.SaleOrder, null=True, blank=True, PROTECT, related_name comprobante_direct
- [x] T019 [P] Add customer FK to Comprobante in `backend/apps/facturacion/models.py` — to ventas.Customer, null=True, blank=True, PROTECT, related_name comprobantes
- [x] T020 [P] Add emitter_condicion_iva to ARCACredential in `backend/apps/facturacion/models.py` — PositiveSmallIntegerField, CondicionIVA choices, default RESPONSABLE_INSCRIPTO
- [x] T021 Add Comprobante validation in `backend/apps/facturacion/models.py` — if sale_order is set, customer must equal sale_order.customer

### Migrations

- [x] T022 Generate ventas initial migration — `python manage.py makemigrations ventas`; verify constraints, indexes, FKs
- [x] T023 [P] Generate facturacion migration for new FKs — `python manage.py makemigrations facturacion`; verify nullable fields
- [x] T024 [P] Generate inventario migration for status/FKs — `python manage.py makemigrations inventario`; verify default COMMITTED
- [x] T025 Apply all migrations and verify — `python manage.py migrate`; confirm all tables created correctly

### RLS Policies

- [x] T026 Create RLS policies for ventas tables in `backend/database/sql/ventas_rls.sql` — ENABLE ROW LEVEL SECURITY + tenant_isolation policies for ventas_customer, ventas_saleorder, ventas_saleorderitem

### Serializers

- [x] T027 [P] Create CustomerSerializer in `backend/apps/ventas/serializers.py` — explicit fields, CUIT validation via validate_cuit(), condicion_iva_display read-only computed field
- [x] T028 [P] Create SaleOrderSerializer in `backend/apps/ventas/serializers.py` — nested customer/branch read, status read-only, totals read-only, confirmed_by read-only; comprobante_id and comprobante nested read via reverse accessor `comprobante_direct` (returns null if no linked invoice); create accepts customer_id (UUID), branch_id (UUID)
- [x] T029 [P] Create SaleOrderItemSerializer in `backend/apps/ventas/serializers.py` — nested product read, subtotal/iva_amount read-only auto-calculated; create accepts product_id (UUID), quantity, unit_price
- [x] T030 Create SaleOrderDetailSerializer in `backend/apps/ventas/serializers.py` — extends SaleOrderSerializer with nested items list (SaleOrderItemSerializer many=True) and comprobante summary

### Views

- [x] T031 [P] Create CustomerViewSet in `backend/apps/ventas/views.py` — ModelViewSet with CRUD; SearchFilter on razon_social/cuit; filterset for is_active, condicion_iva; CursorPagination ordered by -created_at
- [x] T032 [P] Create SaleOrderViewSet in `backend/apps/ventas/views.py` — ModelViewSet (list/create/retrieve/update/destroy); filterset for status, customer, date_from, date_to; block PATCH for non-DRAFT orders; block DELETE for non-DRAFT orders (return 409 order_not_draft); use SaleOrderDetailSerializer for retrieve
- [x] T033 [P] Create SaleOrderItemViewSet in `backend/apps/ventas/views.py` — nested under SaleOrder (get order_id from URL kwarg); list/create/update/delete; block all mutations when parent.status != DRAFT; reject duplicate product_id in order
- [x] T034 [P] Update ComprobanteSerializer in `backend/apps/facturacion/serializers.py` — add sale_order and customer as read-only nested fields; backward compatible (null allowed)

### URL Configuration

- [x] T035 Create URL router in `backend/apps/ventas/urls.py` — register CustomerViewSet at `customers/`, SaleOrderViewSet at `orders/`, SaleOrderItemViewSet nested at `orders/{order_pk}/items/`
- [x] T036 Include ventas URLs in `backend/gravitea/urls.py` — add `path('api/v1/ventas/', include('apps.ventas.urls'))` to urlpatterns

### Admin & OpenAPI

- [x] T037 [P] Register admin classes in `backend/apps/ventas/admin.py` — CustomerAdmin (list_display: cuit, razon_social, condicion_iva, is_active; search: cuit, razon_social), SaleOrderAdmin (list_display: id, customer, status, total_amount; list_filter: status), SaleOrderItemAdmin inline
- [x] T038 [P] Add drf-spectacular @extend_schema decorators to all ViewSet actions in `backend/apps/ventas/views.py` — request/response examples per api-contract.md

**Checkpoint**: All CRUD endpoints functional. `python manage.py migrate` clean. Existing 334 facturacion tests still pass. Customer CUIT validation rejects invalid check digits.

---

## Phase 3: User Story 1 — Complete Sale with Electronic Invoice Authorization (Priority: P1) MVP

**Goal**: A sales representative creates a sale order, confirms it to reserve inventory, and obtains CAE from ARCA — the complete revenue-to-compliance workflow.

**Independent Test**: Create sale order with valid customer and products → confirm → authorize with mock ARCA → receive CAE, stock committed, status INVOICED.

**FRs**: FR-004, FR-008, FR-011, FR-012, FR-013, FR-014, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-025, FR-026, FR-027, FR-029, FR-030, FR-038

### Implementation for User Story 1

- [x] T039 [US1] Create SaleService class scaffold in `backend/apps/ventas/services/sale_service.py` — class with __init__ accepting StockService and InvoiceService dependencies
- [x] T040 [US1] Implement SaleService.confirm_sale() in `backend/apps/ventas/services/sale_service.py` — @transaction.atomic: validate order has items → validate order is DRAFT → for each item: select_for_update on BranchStock, check available_quantity >= requested → call StockService.reserve_stock() per item → create Comprobante DRAFT via invoice-from-sale helper → link comprobante to SaleOrder → set status=CONFIRMED, confirmed_at=now
- [x] T041 [US1] Implement invoice-from-sale helper in `backend/apps/ventas/services/sale_service.py` — determine cbte_tipo via resolver_tipo_comprobante(credential.emitter_condicion_iva, customer.condicion_iva); populate Comprobante fields: imp_total, imp_neto, imp_iva, doc_tipo, doc_nro from customer; set concepto=PRODUCTOS; return Comprobante DRAFT
- [x] T042 [US1] Implement IVA breakdown (AlicIva creation) in `backend/apps/ventas/services/sale_service.py` — group SaleOrderItems by tax_rate → create AlicIva per group: map tax_rate to AlicIvaId enum, BaseImp=sum(subtotals), Importe=sum(iva_amounts); handle multiple rates (21%, 10.5%, 27%, 0%)
- [x] T043 [US1] Implement amount mapping in `backend/apps/ventas/services/sale_service.py` — imp_total=total_amount, imp_neto=subtotal, imp_iva=total_iva, imp_trib=0, imp_op_ex/imp_tot_conc based on condicion_iva; validate imp_total == sum of components (ARCA balance check)
- [x] T044 [US1] Set doc_tipo/doc_nro from Customer in `backend/apps/ventas/services/sale_service.py` — Comprobante.doc_tipo=customer.doc_tipo, doc_nro=customer.cuit; validate doc_tipo rules per cbte_tipo (Type A requires CUIT)
- [x] T045 [US1] Implement SaleService.authorize_sale() in `backend/apps/ventas/services/sale_service.py` — validate order is CONFIRMED with linked comprobante → call InvoiceService.authorize_comprobante() → on Resultado A: commit stock via StockService.commit_reservation(), set status=INVOICED, invoiced_at=now → on Resultado O: same as A but include observaciones in response → return result
- [x] T046 [US1] Update StockService.reserve_stock() in `backend/apps/inventario/services/stock_service.py` — create StockMovement with status=RESERVED, sale_order FK, movement_type=SALE, negative quantity_delta; update StockSnapshot.reserved_quantity
- [x] T047 [US1] Implement StockService.commit_reservation() in `backend/apps/inventario/services/stock_service.py` — find RESERVED movements for sale_order → transition each to COMMITTED → set comprobante FK → update StockSnapshot.reserved_quantity (decrease reserved, quantity stays same since movement was already recorded)
- [x] T048 [US1] Add `confirm` action to SaleOrderViewSet in `backend/apps/ventas/views.py` — @action(detail=True, methods=['post'], url_path='confirm'); call SaleService.confirm_sale(); return 200 with confirmation result including stock_reservations list and comprobante summary
- [x] T049 [US1] Add `authorize` action to SaleOrderViewSet in `backend/apps/ventas/views.py` — @action(detail=True, methods=['post'], url_path='authorize'); call SaleService.authorize_sale(); return 200 with comprobante details including CAE, or error response
- [x] T050 [US1] Add `invoice` retrieval action to SaleOrderViewSet in `backend/apps/ventas/views.py` — @action(detail=True, methods=['get'], url_path='invoice'); return linked comprobante via ComprobanteSerializer or 404
- [x] T051 [US1] Verify CbteNro sequencing for sale-originated invoices in `backend/apps/facturacion/services.py` — Added authorize_comprobante() to InvoiceService; updates existing DRAFT in-place instead of creating duplicate
- [x] T052 [US1] Verify fiscal QR generation for sale invoices in `backend/apps/facturacion/qr.py` — Verified: QR generation uses only Comprobante fields, no sale_order dependency
- [x] T053 [US1] Add idempotency checks in `backend/apps/ventas/services/sale_service.py` — confirm_sale: return current state if already CONFIRMED (don't double-confirm); authorize_sale: reject if not CONFIRMED, reject if already has CAE
- [x] T054 [US1] Add authorize endpoint on ComprobanteViewSet in `backend/apps/facturacion/views.py` — POST /api/v1/facturacion/comprobantes/{id}/authorize/; delegates to InvoiceService; alternative entry point for authorization

**Checkpoint**: Complete happy path works: create customer → create order → add items → confirm (stock reserved, invoice DRAFT created) → authorize (mock ARCA returns A, stock committed, status INVOICED, CAE stored). Fiscal QR generated.
**TDD**: Write T090, T091, T094 tests before/alongside T039-T054 implementation.

---

## Phase 4: User Story 2 — Recover from Authorization Rejection (Priority: P1)

**Goal**: When ARCA rejects an invoice, the system releases reserved stock and allows the user to correct data and retry without losing the sale.

**Independent Test**: Submit invoice with invalid data → ARCA returns R → stock released, sale reverts to CONFIRMED → correct data → re-authorize successfully.

**FRs**: FR-015, FR-028, FR-031, FR-032, FR-033

### Implementation for User Story 2

- [x] T055 [US2] Implement StockService.cancel_reservation() in `backend/apps/inventario/services/stock_service.py` — find RESERVED movements for sale_order → transition each to CANCELLED → update StockSnapshot.reserved_quantity (decrease reserved, increase available)
- [x] T056 [US2] Implement rejection handling in SaleService.authorize_sale() in `backend/apps/ventas/services/sale_service.py` — on Resultado R: call StockService.cancel_reservation() → SaleOrder status stays CONFIRMED (not DRAFT) for retry → Comprobante set to RECHAZADO (done by InvoiceService) → return error with ARCA error details
- [x] T057 [US2] Implement ARCA rejection error mapping in `backend/apps/ventas/services/sale_service.py` — map ARCA error codes to structured response: {"error": {"code": "arca_rejected", "resultado": "R", "errors": [...], "observaciones": [...], "sale_status": "CONFIRMED"}}
- [x] T058 [US2] Store ARCA errors in Comprobante in `backend/apps/facturacion/models.py` — verify arca_errors JSONField stores rejection details; arca_response stores full response
- [x] T059 [US2] Ensure retry uses same CbteNro in `backend/apps/ventas/services/sale_service.py` — on re-authorization after rejection: existing Comprobante.cbte_nro is preserved; InvoiceService queries FECompUltimoAutorizado to verify next number matches
- [x] T060 [US2] Add re-authorization flow in `backend/apps/ventas/services/sale_service.py` — when authorize_sale called on CONFIRMED order with RECHAZADO comprobante: re-validate stock availability (may have changed since rejection) → if insufficient return insufficient_stock error → re-reserve stock → transition comprobante from RECHAZADO to VALIDANDO → re-submit to ARCA with same cbte_nro

**Checkpoint**: Rejection flow works: authorize → ARCA rejects → stock released, order stays CONFIRMED → fix data → re-authorize → success. Error details include ARCA codes.
**TDD**: Write T092 tests before/alongside T055-T060 implementation.

---

## Phase 5: User Story 3 — Prevent Stock Overselling (Priority: P1)

**Goal**: The system prevents overselling by using database-level locks when reserving stock, ensuring concurrent requests don't exceed available quantities.

**Independent Test**: Simulate two concurrent confirm_sale() calls for same product with limited stock → only one succeeds, other gets InsufficientStockError.

**FRs**: FR-008, FR-012, FR-013

### Implementation for User Story 3

- [x] T061 [US3] Ensure select_for_update on BranchStock in SaleService.confirm_sale() in `backend/apps/ventas/services/sale_service.py` — use BranchStock.objects.select_for_update().get(product=item.product, branch=order.branch) for each item before checking availability; prevents TOCTOU race conditions
- [x] T062 [US3] Update available stock calculation in `backend/apps/inventario/services/stock_service.py` — available = snapshot.quantity - snapshot.reserved_quantity; ensure this reflects current RESERVED movements accurately
- [x] T063 [US3] Implement InsufficientStockError with rich details in `backend/apps/inventario/services/stock_service.py` — include product_id, product_sku, product_name, available quantity, requested quantity, branch name in exception
- [x] T064 [US3] Format insufficient stock API error response in `backend/apps/ventas/views.py` — catch InsufficientStockError in confirm action; return 409 with {"error": {"code": "insufficient_stock", "message": "...", "details": {product_id, product_sku, available, requested, branch}}}
- [x] T065 [US3] Handle empty order confirmation attempt in `backend/apps/ventas/services/sale_service.py` — return 409 with {"error": {"code": "order_empty", "message": "Cannot confirm an order with no items."}}

**Checkpoint**: Concurrent stock protection verified: two simultaneous confirmations for product with qty=5, each requesting 3 → first succeeds (reserves 3), second fails with insufficient_stock (only 2 available).
**TDD**: Write T097 concurrent test before/alongside T061-T065 implementation.

---

## Phase 6: User Story 4 — Manage Customer Tax Status (Priority: P2)

**Goal**: Customers are registered with their IVA condition, and the system auto-determines invoice type (A/B/C) based on customer tax status.

**Independent Test**: Create customer with CondicionIVA=RI → confirm sale → invoice is Type A. Create customer with CondicionIVA=CF → confirm sale → invoice is Type B.

**FRs**: FR-001, FR-002, FR-003, FR-004, FR-018

### Implementation for User Story 4

- [x] T066 [US4] Verify invoice type auto-determination in SaleService in `backend/apps/ventas/services/sale_service.py` — confirm resolver_tipo_comprobante(credential.emitter_condicion_iva, customer.condicion_iva) produces correct CbteTipo: RI→RI=1(A), RI→CF=6(B), RI→Mono=11(C), RI→Exento=6(B)
- [x] T067 [US4] Implement Customer deletion protection in `backend/apps/ventas/views.py` — override destroy() on CustomerViewSet: check if customer has linked SaleOrders; if yes, return 409 {"error": {"code": "customer_has_orders", "message": "Cannot delete customer with existing sale orders. Deactivate instead."}}
- [x] T068 [US4] Validate doc_tipo rules per invoice type in `backend/apps/ventas/services/sale_service.py` — Type A requires doc_tipo 80 (CUIT), 86 (CUIL), or 87 (CDI); validate before creating comprobante; reject with clear error if incompatible
- [x] T069 [US4] Implement condicion_iva_display on CustomerSerializer in `backend/apps/ventas/serializers.py` — read-only SerializerMethodField returning human-readable IVA condition name from CondicionIVA.choices
- [x] T070 [US4] Validate CUIT on sale order creation in `backend/apps/ventas/services/sale_service.py` — ensure customer has valid CUIT and condicion_iva before allowing confirm_sale; reject with 400 if customer data incomplete

**Checkpoint**: Create customers with different CondicionIVA values → each sale auto-generates correct invoice type. Invalid CUIT rejected at customer creation. Customer with orders cannot be deleted.
**TDD**: Write T082, T083, T087, T094 tests before/alongside T066-T070 implementation.

---

## Phase 7: User Story 5 — Recover from Network Timeouts (Priority: P2)

**Goal**: When network timeouts interrupt ARCA communication, the system queries ARCA for authorization status and reconciles state accordingly.

**Independent Test**: Simulate timeout during FECAESolicitar → system queries FECompUltimoAutorizado → if CAE was granted: commit stock + INVOICED; if not: leave CONFIRMED for retry.

**FRs**: FR-034, FR-035

### Implementation for User Story 5

- [x] T071 [US5] Implement timeout handling in SaleService.authorize_sale() in `backend/apps/ventas/services/sale_service.py` — catch timeout exception from InvoiceService → call InvoiceService._recover_from_timeout() → if CAE recovered: commit stock, set INVOICED → if not recovered: leave CONFIRMED, return timeout response
- [x] T072 [US5] Format timeout API response in `backend/apps/ventas/views.py` — return 504 with {"error": {"code": "arca_timeout", "message": "...", "recovery_attempted": true, "recovered": bool, "sale_status": "CONFIRMED" or "INVOICED"}}
- [x] T073 [US5] Implement certificate expiration check in `backend/apps/ventas/services/sale_service.py` — before authorize_sale calls InvoiceService: validate ARCACredential certificate is not expired; return 502 with {"error": {"code": "arca_auth_failed", "message": "Certificate expired..."}} if invalid
- [x] T074 [US5] Ensure retry safety after timeout in `backend/apps/ventas/services/sale_service.py` — if timeout recovery found no CAE: Comprobante retains same cbte_nro; next authorize_sale attempt uses same number (not incremented)

**Checkpoint**: Timeout recovery works for both paths: (1) CAE was actually granted → stock committed, INVOICED; (2) CAE was not granted → CONFIRMED, retry-ready with same CbteNro.
**TDD**: Write T093 timeout test before/alongside T071-T074 implementation.

---

## Phase 8: User Story 6 — Track Sale-to-Invoice-to-Stock Audit Trail (Priority: P3)

**Goal**: All state transitions are logged, and stock movements link back to originating sale orders and authorized invoices for audit compliance.

**Independent Test**: Complete a sale → verify stock movement has sale_order FK and comprobante FK → verify SaleOrder status transitions logged with timestamps.

**FRs**: FR-016, FR-039

### Implementation for User Story 6

- [x] T075 [US6] Implement audit logging for SaleOrder status transitions in `backend/apps/ventas/models.py` — log via Django logging framework with structured JSON: timestamp, user_id, sale_order_id, previous_status, new_status, reason
- [x] T076 [US6] Verify StockMovement traceability in `backend/apps/inventario/services/stock_service.py` — ensure all sale-originated movements have sale_order FK set; committed movements also have comprobante FK set
- [x] T077 [US6] Implement cross-tenant reference error in `backend/apps/ventas/views.py` — catch ValidationError from _validate_tenant_references; return 403 {"error": {"code": "cross_tenant_reference", "message": "IDOR violation detected"}}
- [x] T078 [US6] Add status transition logging to SaleService in `backend/apps/ventas/services/sale_service.py` — log confirm_sale (DRAFT→CONFIRMED), authorize_sale success (CONFIRMED→INVOICED), authorize_sale rejection (stock released), authorize_sale timeout (recovery result)

**Checkpoint**: Complete sale → stock movements have sale_order_id and comprobante_id → SaleOrder transitions logged → cross-tenant access returns 403.
**TDD**: Write T095 tenant isolation test before/alongside T075-T078 implementation.

---

## Phase 9: Testing

**Purpose**: Comprehensive test suite covering unit, integration, security, and performance. Tests run externally per token efficiency protocol.

### Test Fixtures

- [x] T079 Create customer test fixtures in `backend/tests/ventas/conftest.py` — fixture_customer_ri (CondicionIVA=1, valid CUIT), fixture_customer_cf (CondicionIVA=5), fixture_customer_mono (CondicionIVA=6), fixture_customer_exento (CondicionIVA=4)
- [x] T080 [P] Create product/stock test fixtures in `backend/tests/ventas/conftest.py` — fixture products with BranchStock at specific branch; pre-populated quantities for testing reservations
- [x] T081 [P] Create ARCA mock fixtures in `backend/tests/ventas/conftest.py` — mock WSFEv1Client: Resultado A (success), Resultado O (observed), Resultado R (rejected), timeout; mock WSAA auth returns token/sign

### Unit Tests

- [x] T082 [P] Unit tests for CUIT validation in `backend/tests/ventas/unit/test_cuit_validation.py` — valid CUITs, invalid check digits, wrong length, non-numeric, edge cases (check=0, check=10→9)
- [x] T083 [P] Unit tests for Customer model in `backend/tests/ventas/unit/test_customer_model.py` — creation, CUIT uniqueness per tenant, condicion_iva choices, is_active default, clean() calls validate_cuit
- [x] T084 [P] Unit tests for SaleOrder model in `backend/tests/ventas/unit/test_sale_order_model.py` — valid transitions (DRAFT→CONFIRMED, CONFIRMED→INVOICED, CONFIRMED→DRAFT), invalid transitions (DRAFT→INVOICED, INVOICED→anything), immutability for INVOICED
- [x] T085 [P] Unit tests for SaleOrderItem model in `backend/tests/ventas/unit/test_sale_order_item.py` — auto-calculate subtotal/iva_amount, parent status lock (reject edit when CONFIRMED), unique product per order constraint
- [x] T086 [P] Unit tests for StockMovement status in `backend/tests/inventario/test_movement_status.py` — RESERVED→COMMITTED ok, RESERVED→CANCELLED ok, COMMITTED→anything blocked, field changes on RESERVED blocked, default COMMITTED for new movements

### Integration Tests

- [x] T087 Integration tests for Customer CRUD API in `backend/tests/ventas/integration/test_customer_api.py` — list with filters (search, is_active, condicion_iva), create (CUIT validation, 409 duplicate), retrieve, update, delete (409 if has orders)
- [x] T088 [P] Integration tests for SaleOrder CRUD API in `backend/tests/ventas/integration/test_sale_order_api.py` — create, list (status/customer/date filters), retrieve (nested items), update (DRAFT only, 409 if CONFIRMED)
- [x] T089 [P] Integration tests for SaleOrderItem API in `backend/tests/ventas/integration/test_sale_order_item_api.py` — add/update/delete items, auto-recalculation of order totals, duplicate product 409, parent status lock
- [x] T090 Integration tests for confirm_sale flow in `backend/tests/ventas/integration/test_sale_flow.py` — 12 tests: confirm creates RESERVED movements + Comprobante DRAFT, order status=CONFIRMED, idempotency, empty items, wrong status
- [x] T091 Integration tests for authorize_sale flow in `backend/tests/ventas/integration/test_sale_flow.py` — 10 tests: mock ARCA success: stock COMMITTED, status=INVOICED, CAE stored; mock observed: same but includes observaciones; rejection, CAE duplication guard
- [x] T092 Integration tests for rejection recovery in `backend/tests/ventas/integration/test_sale_flow.py` — 8 tests: mock ARCA rejection: stock CANCELLED (released), order stays CONFIRMED, error details returned; network error handling; re-authorize succeeds after rejection and network error
- [x] T093 Integration tests for timeout recovery in `backend/tests/ventas/test_sale_service.py` — mock timeout then FECompConsultar; test both paths: CAE recovered (INVOICED) and CAE not found (CONFIRMED for retry)
- [x] T094 Integration tests for invoice type determination in `backend/tests/ventas/unit/test_services.py` — 13 tests: RI→RI=TypeA, RI→CF=TypeB, RI→Mono=TypeC, RI→Exento=TypeB, plus ARCA balance equation validation

### Security Tests

- [x] T095 Security tests for tenant isolation in `backend/tests/ventas/security/test_tenant_isolation.py` — cross-tenant customer access blocked, cross-tenant order access blocked, cross-tenant item inherits tenant
- [x] T096 [P] Security tests for status transition enforcement in `backend/tests/ventas/security/test_status_transitions.py` — direct status manipulation via model.save() properly validated; only valid transitions allowed

### Performance Tests

- [x] T097 Concurrent stock reservation test in `backend/tests/ventas/integration/test_sale_flow.py` — ThreadPoolExecutor with 50 concurrent confirm_sale calls for same product with qty=25; verify total reserved never exceeds available; no overselling, no deadlocks

### Regression

- [ ] T098 Run existing facturacion test suite (334 tests) — verify zero regressions from Comprobante FK additions
- [ ] T099 Run existing inventario test suite — verify zero regressions from StockMovement status/FK additions
- [ ] T100 Run full test suite — all existing + new tests pass; `pytest --tb=short -q`

**Checkpoint**: >90% coverage on ventas module. All 334 existing facturacion tests pass. Zero cross-tenant leakage. 50 concurrent sales pass.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Docker config, OpenAPI validation, seed data, deployment readiness

- [ ] T101 [P] Update docker-compose.yml — ensure ventas module included in backend service; migration ordering: core → auth → inventario → facturacion → ventas
- [ ] T102 [P] Create migration dependency chain in `backend/apps/ventas/migrations/0001_initial.py` — verify dependencies list includes facturacion (Comprobante FK) and inventario (Product FK)
- [ ] T103 [P] Create RLS policy migration or management command for ventas tables in `backend/database/sql/ventas_rls.sql` — apply via RunSQL in Django migration
- [ ] T104 Validate OpenAPI schema — generate schema via `python manage.py spectacular --file schema.yml`; verify all new ventas endpoints documented with request/response examples
- [ ] T105 [P] Create data seed management command in `backend/apps/ventas/management/commands/seed_ventas.py` — create sample customers (RI, CF, Mono), sample products with stock, sample orders for manual testing
- [ ] T106 [P] Update backend README in `backend/README.md` — add ventas module description, new endpoints, test commands
- [ ] T107 [P] Standardize all error responses across ventas views in `backend/apps/ventas/views.py` — verify all errors follow contract format {"error": {"code": "...", "message": "...", "details": {}}}
- [ ] T108 Final integration smoke test — full flow: create customer → create order → add items → confirm → authorize (mocked) → verify QR → verify stock committed → verify audit trail

**Checkpoint**: Docker build succeeds. All migrations apply cleanly. OpenAPI schema validates. Smoke test passes end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — core MVP path
- **US2 (Phase 4)**: Depends on US1 — rejection extends authorization flow
- **US3 (Phase 5)**: Depends on Foundational — can run parallel with US1 (stock locking is independent)
- **US4 (Phase 6)**: Depends on Foundational — can run parallel with US1 (invoice type logic is independent)
- **US5 (Phase 7)**: Depends on US1 — timeout extends authorization flow
- **US6 (Phase 8)**: Depends on Foundational — can run parallel with US1 (logging is independent)
- **Testing (Phase 9)**: Depends on US1–US6 completion
- **Polish (Phase 10)**: Depends on Testing completion

### User Story Dependencies

```
Phase 1: Setup
    │
    v
Phase 2: Foundational (BLOCKS ALL)
    │
    ├──────────────────────────────────────┐
    │                                      │
    v                                      v
Phase 3: US1 (P1) ─── MVP ───┐    Phase 5: US3 (P1) [parallel]
    │                          │    Phase 6: US4 (P2) [parallel]
    ├─────────┐                │    Phase 8: US6 (P3) [parallel]
    v         v                │
Phase 4:   Phase 7:           │
US2 (P1)   US5 (P2)           │
    │         │                │
    v         v                v
Phase 9: Testing ◄────────────┘
    │
    v
Phase 10: Polish
```

### Within Each User Story

- Models/enhancements before service logic
- Service logic before view actions
- View actions before error formatting
- Core implementation before edge cases

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T012-T15 (StockMovement changes) parallel with T18-T20 (Comprobante changes)
- T027-T29 (serializers) parallel with T37 (admin)
- T031-T33 (views) parallel with T34 (Comprobante serializer update)

**Across User Stories**:
- US3 (Phase 5), US4 (Phase 6), US6 (Phase 8) can start as soon as Phase 2 completes
- US2 (Phase 4) and US5 (Phase 7) require US1 (Phase 3) completion

**Within Phase 9 (Testing)**:
- T082-T086 (unit tests) all parallel
- T087-T089 (CRUD tests) parallel
- T095-T096 (security tests) parallel with integration tests

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Batch 1: All model changes in parallel (different files)
Task T012: "StockMovementStatus enum in backend/apps/inventario/models.py"
Task T018: "sale_order OneToOneField to Comprobante in backend/apps/facturacion/models.py"
Task T019: "customer FK to Comprobante in backend/apps/facturacion/models.py"
Task T020: "emitter_condicion_iva to ARCACredential in backend/apps/facturacion/models.py"

# Batch 2: All serializers in parallel (same file but independent sections)
Task T027: "CustomerSerializer in backend/apps/ventas/serializers.py"
Task T028: "SaleOrderSerializer in backend/apps/ventas/serializers.py"
Task T029: "SaleOrderItemSerializer in backend/apps/ventas/serializers.py"
Task T034: "Update ComprobanteSerializer in backend/apps/facturacion/serializers.py"

# Batch 3: All views in parallel
Task T031: "CustomerViewSet in backend/apps/ventas/views.py"
Task T032: "SaleOrderViewSet in backend/apps/ventas/views.py"
Task T033: "SaleOrderItemViewSet in backend/apps/ventas/views.py"
```

## Parallel Example: Phase 9 (Testing)

```bash
# All unit tests in parallel (different test files)
Task T082: "CUIT validation tests"
Task T083: "Customer model tests"
Task T084: "SaleOrder model tests"
Task T085: "SaleOrderItem model tests"
Task T086: "StockMovement status tests"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (complete sale + invoice + CAE)
4. **STOP and VALIDATE**: Test US1 independently with mock ARCA
5. Deploy/demo if ready — this alone delivers the core revenue workflow

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → **Deploy/Demo (MVP!)**
3. Add US2 (rejection) + US3 (overselling) → Test → Deploy (P1 complete)
4. Add US4 (customer tax) + US5 (timeout) → Test → Deploy (P2 complete)
5. Add US6 (audit trail) → Test → Deploy (P3 complete)
6. Testing + Polish → Final release

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: US1 (Phase 3) → US2 (Phase 4) → US5 (Phase 7)
- **Developer B**: US3 (Phase 5) → US4 (Phase 6) → US6 (Phase 8)
- **Developer C**: Test fixtures → Unit tests → Integration tests (Phase 9)

Each developer works on different files, minimizing merge conflicts.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [USx] label maps task to specific user story for traceability
- Each user story is independently testable after its phase completes
- All tests run EXTERNALLY per token efficiency protocol — never inside Claude Code
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- 334 existing facturacion tests must pass at every checkpoint
