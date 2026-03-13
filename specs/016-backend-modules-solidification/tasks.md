# Tasks: Backend Modules Solidification

**Input**: Design documents from `/specs/016-backend-modules-solidification/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — spec requires 60+ compras tests (SC-004), 15+ reportes tests (SC-008).

**Organization**: Tasks grouped by user story. US1 is foundational (blocks US2-US4). US5 can start after Phase 1 setup.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US7)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/apps/`, `backend/gravitea/`, `tests/`
- **Database SQL**: `backend/database/sql/`
- **Management commands**: `backend/apps/{module}/management/commands/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create both new Django app skeletons and register them in the project

- [x] T001 [P] Create compras app skeleton — backend/apps/compras/__init__.py, apps.py (ComprasConfig, app_label="gravitea_compras"), empty models.py, views.py, serializers.py, services.py, urls.py, admin.py
- [x] T002 [P] Create reportes app skeleton — backend/apps/reportes/__init__.py, apps.py (ReportesConfig, app_label="gravitea_reportes"), empty models.py, views.py, serializers.py, services.py, urls.py, admin.py
- [x] T003 Register apps.compras and apps.reportes in INSTALLED_APPS in backend/gravitea/settings/base.py
- [x] T004 Include compras.urls under /api/v1/compras/ and reportes.urls under /api/v1/reportes/ in backend/gravitea/urls.py

**Checkpoint**: Both apps registered, project starts without errors

---

## Phase 2: User Story 1 — Supplier Migration to Purchases Module (Priority: P1) — FOUNDATIONAL

**Goal**: Move Supplier entity from inventario to compras without data loss, using SeparateDatabaseAndState migration pattern (R-001)

**Independent Test**: Run full existing test suite — 0 new failures. All supplier CRUD works at /api/v1/compras/suppliers/

**Why Foundational**: US2–US4 depend on Supplier being in compras. This MUST complete before any PO work.

### Implementation

- [x] T005 [US1] Copy Supplier model definition to backend/apps/compras/models.py — preserve all encrypted fields (tax_id_encrypted, contact_info_encrypted, email_encrypted, address_encrypted), blind indexes (tax_id_hash, email_hash), Meta class, set db_table="inventario_supplier" to avoid table rename
- [x] T006 [US1] Create SeparateDatabaseAndState migration in backend/apps/compras/migrations/0001_initial.py — state_operations: CreateModel(Supplier) with all fields; database_operations: empty (table already exists)
- [x] T007 [US1] Create SeparateDatabaseAndState migration in backend/apps/inventario/migrations/ — state_operations: DeleteModel("Supplier"); database_operations: empty
- [x] T008 [US1] Update Product.supplier FK to reference "compras.Supplier" in backend/apps/inventario/models.py + create state-only migration for FK target change
- [x] T009 [US1] Move SupplierSerializer to backend/apps/compras/serializers.py — preserve all field definitions, encrypted field handling, CustomFieldsMixin with entity_type="supplier"
- [x] T010 [US1] Move SupplierViewSet to backend/apps/compras/views.py — preserve queryset with select_related, filter backends, search fields
- [x] T011 [US1] Register SupplierViewSet in backend/apps/compras/urls.py under /suppliers/; remove supplier registration from backend/apps/inventario/urls.py
- [x] T012 [US1] Update all test files referencing inventario.Supplier — update imports in tests/performance/test_n_plus_one.py, tests/inventario/test_inventory_api.py, tests/integration/test_custom_fields_e2e.py, and any conftest.py fixtures
- [x] T013 [US1] Write supplier migration verification tests in tests/compras/test_supplier_migration.py — verify data preservation, FK integrity, encrypted field access, custom fields, tenant isolation, CRUD at new URL
- [x] T014 [US1] GATE: Full regression — run entire test suite, verify 0 new failures from supplier migration

**Checkpoint**: Supplier lives in compras. All existing tests pass. Phase 2+ can begin.

---

## Phase 3: User Story 2 — Purchase Order Lifecycle (Priority: P1)

**Goal**: Implement PurchaseOrder + PurchaseOrderItem with state machine (DRAFT→CONFIRMED→PARTIAL_RECEIVED→RECEIVED→CANCELLED)

**Independent Test**: Create PO with items, confirm it, verify state transitions, verify line items lock after confirmation, verify tenant isolation

**Dependencies**: Phase 2 (US1) must be complete — PO references compras.Supplier

### Implementation

- [x] T015 [US2] Create PurchaseOrderStatus TextChoices + PURCHASE_ORDER_TRANSITIONS dict + PurchaseOrder model (tenant_id FK, supplier FK RESTRICT, order_number unique per tenant, status, order_date, expected_delivery_date, notes, custom_data JSONField, total_amount DECIMAL(17,3)) in backend/apps/compras/models.py
- [x] T016 [US2] Create PurchaseOrderItem model (purchase_order FK CASCADE, product FK RESTRICT, quantity DECIMAL(17,3) CHECK > 0, unit_price DECIMAL(17,3) CHECK >= 0, line_total DECIMAL(17,3) computed, received_quantity DECIMAL(17,3) default=0) in backend/apps/compras/models.py
- [x] T017 [US2] Create migration for PurchaseOrder + PurchaseOrderItem tables with CHECK constraints and indexes in backend/apps/compras/migrations/
- [x] T018 [US2] Create RLS policies for compras_purchaseorder and compras_purchaseorderitem tables in backend/database/sql/ — tenant_id isolation matching existing RLS pattern
- [x] T019 [US2] Create PurchaseOrderItemSerializer + PurchaseOrderSerializer (nested writable items, auto-compute line_total and total_amount) in backend/apps/compras/serializers.py — follow SaleOrder nested pattern from ventas
- [x] T020 [US2] Create PurchaseOrderViewSet in backend/apps/compras/views.py — CRUD, @action confirm (DRAFT→CONFIRMED), @action cancel (DRAFT|CONFIRMED|PARTIAL_RECEIVED→CANCELLED), enforce mutable fields by state
- [x] T021 [US2] Register purchase-orders/ URLs including {id}/confirm/ and {id}/cancel/ actions in backend/apps/compras/urls.py
- [x] T022 [P] [US2] Write PO CRUD + tenant isolation tests in tests/compras/test_purchase_order_crud.py — create, read, update, delete, list with filters, nested items, total calculation, cross-tenant rejection
- [x] T023 [P] [US2] Write PO state machine tests in tests/compras/test_purchase_order_state_machine.py — all valid transitions, all invalid transitions, field mutability per state, line item lock after confirm
- [x] T024 [US2] GATE: Regression green — all existing + new PO tests pass

**Checkpoint**: Full PO lifecycle works. Can create, confirm, cancel. Line items compute totals.

---

## Phase 4: User Story 3 — Goods Receipt and Stock Update (Priority: P1)

**Goal**: Record goods receipts against confirmed POs, auto-create StockMovements (type=PURCHASE), auto-transition PO state, enforce immutability and over-receipt rejection

**Independent Test**: Confirm a PO, record partial receipt, verify stock movement created, verify PO state is PARTIAL_RECEIVED, record remaining, verify PO is RECEIVED, verify over-receipt rejected

**Dependencies**: Phase 3 (US2) must be complete — GR references PurchaseOrder + PurchaseOrderItem

### Implementation

- [x] T025 [US3] Create GoodsReceipt model (tenant_id FK, purchase_order FK RESTRICT, receipt_number unique per tenant, receipt_date, received_by FK AppUser NULL, notes) in backend/apps/compras/models.py — no update/delete operations (immutable)
- [x] T026 [US3] Create GoodsReceiptLine model (goods_receipt FK CASCADE, purchase_order_item FK RESTRICT, product FK RESTRICT denormalized, quantity_received DECIMAL(17,3) CHECK > 0) in backend/apps/compras/models.py
- [x] T027 [US3] Create migration for GoodsReceipt + GoodsReceiptLine tables with CHECK constraints in backend/apps/compras/migrations/
- [x] T028 [US3] Create RLS policies for compras_goodsreceipt and compras_goodsreceiptline tables in backend/database/sql/
- [x] T029 [US3] Create GoodsReceiptService in backend/apps/compras/services.py — validate PO is CONFIRMED|PARTIAL_RECEIVED, validate no over-receipt (received + existing <= ordered per line), create GoodsReceiptLine entries, create StockMovement(type=PURCHASE) per line via StockService, update POItem.received_quantity, auto-transition PO state based on cumulative quantities
- [x] T030 [US3] Create GoodsReceiptSerializer (nested GoodsReceiptLineSerializer) in backend/apps/compras/serializers.py — create-only (no update), validate lines reference valid POItems
- [x] T031 [US3] Create GoodsReceiptViewSet in backend/apps/compras/views.py — list all receipts, get detail, create via service (nested under PO: /purchase-orders/{id}/goods-receipts/), standalone list at /goods-receipts/, no update/delete endpoints
- [x] T032 [US3] Register goods receipt URLs (nested + standalone) in backend/apps/compras/urls.py
- [x] T033 [P] [US3] Write goods receipt tests in tests/compras/test_goods_receipt.py — create receipt, immutability (reject PUT/PATCH/DELETE), over-receipt rejection, partial receipt, full receipt, receipt against non-confirmed PO rejected, tenant isolation, partial receipt then PO cancellation (verify already-created stock movements are preserved)
- [x] T034 [P] [US3] Write stock integration tests in tests/compras/test_stock_integration.py — StockMovement created with type=PURCHASE, correct quantity, product reference, PO traceability, stock level updated, POItem.received_quantity accumulated
- [x] T035 [US3] GATE: Regression green — all existing + new GR/stock tests pass

**Checkpoint**: Full procurement loop works. PO→Confirm→Receive→Stock updated. Immutability enforced.

---

## Phase 5: User Story 4 — Purchase Order Custom Fields (Priority: P2)

**Goal**: Extend JSONB custom fields framework to PurchaseOrder entity type

**Independent Test**: Create TenantFieldDefinition for purchase_order, create PO with custom_data, verify validation, verify merge on update

**Dependencies**: Phase 3 (US2) must be complete — PO model must exist. Independent of US3/US5.

### Implementation

- [x] T036 [US4] Add PURCHASE_ORDER = "purchase_order" to TenantFieldDefinition.EntityType choices in backend/apps/core/models/customization.py + create migration
- [x] T037 [US4] Apply CustomFieldsMixin to PurchaseOrderSerializer with entity_type="purchase_order" in backend/apps/compras/serializers.py — ensure custom_data field is included, validation on create/update, merge on partial update
- [x] T038 [US4] Write PO custom fields tests in tests/compras/test_custom_fields.py — define fields (text, number, required), create PO with valid custom_data, create PO missing required field (rejected), update with partial custom_data (merge behavior), tenant without definitions (custom_data optional), attempt to update custom_data on confirmed PO (rejected — locked after confirmation per data-model mutable fields rules)
- [x] T039 [US4] GATE: Regression green

**Checkpoint**: Custom fields work on POs identically to products/customers/suppliers/sale orders.

---

## Phase 6: User Story 5 — Reporting Module Infrastructure (Priority: P2)

**Goal**: Create REPORTES module skeleton — models, CRUD endpoints, read-only data access layer. No report generation logic.

**Independent Test**: Create a ReportDefinition, create a SavedReport referencing it, create an ExportJob referencing the SavedReport. Verify tenant isolation on all three.

**Dependencies**: Phase 1 (Setup) must be complete. Independent of US1–US4 — can start in parallel after Phase 1.

### Implementation

- [x] T040 [US5] Create ReportDefinition model (tenant_id FK, name, report_type TextChoices [sales|stock|purchases|fiscal|accounting_export], parameters JSONField, filters JSONField, output_format TextChoices [PDF|EXCEL|CSV], is_active boolean) in backend/apps/reportes/models.py
- [x] T041 [US5] Create SavedReport model (tenant_id FK, report_definition FK CASCADE, generated_at auto, result_metadata JSONField, file_reference CharField NULL, status TextChoices [PENDING|COMPLETED|FAILED]) in backend/apps/reportes/models.py
- [x] T042 [US5] Create ExportJob model (tenant_id FK, saved_report FK CASCADE, export_format TextChoices [PDF|EXCEL|CSV], status TextChoices [PENDING|PROCESSING|COMPLETED|FAILED], file_path CharField NULL, created_at, completed_at NULL) in backend/apps/reportes/models.py
- [x] T043 [US5] Create reportes initial migration in backend/apps/reportes/migrations/
- [x] T044 [US5] Create RLS policies for reportes_reportdefinition, reportes_savedreport, reportes_exportjob tables in backend/database/sql/
- [x] T045 [US5] Create ReportDefinitionSerializer, SavedReportSerializer, ExportJobSerializer in backend/apps/reportes/serializers.py — standard CRUD serializers with tenant isolation
- [x] T046 [US5] Create ReportDefinitionViewSet, SavedReportViewSet, ExportJobViewSet in backend/apps/reportes/views.py — standard ModelViewSets with TenantBoundManager, cursor pagination, filter by type/status
- [x] T047 [US5] Create ReportService with read-only QuerySet methods in backend/apps/reportes/services.py — aggregated sales data, stock level summaries, purchase history, scoped by tenant_id
- [x] T048 [US5] Register reportes URLs in backend/apps/reportes/urls.py — /definitions/, /saved-reports/, /export-jobs/
- [x] T049 [P] [US5] Write report definition CRUD + filter tests in tests/reportes/test_report_definition_crud.py — create, read, update, delete, list with report_type filter, list with is_active filter, tenant isolation
- [x] T050 [P] [US5] Write saved report tests in tests/reportes/test_saved_report.py — create, read, delete, list with status filter, list with report_definition_id filter, tenant isolation
- [x] T051 [P] [US5] Write export job tests in tests/reportes/test_export_job.py — create, read, list with status filter, tenant isolation
- [x] T052 [US5] GATE: Regression green — verify 15+ reportes tests pass

**Checkpoint**: Reportes module operational with 3 entities, basic CRUD, tenant isolation, read-only data access.

---

## Phase 7: User Story 6 — Permission Controls for New Modules (Priority: P2)

**Goal**: Extend role-based permissions to cover purchases and reports modules

**Independent Test**: Create role with purchases.read only → verify can list POs but cannot create. Create role with reports.export → verify can trigger export. Verify no-permission user gets 403.

**Dependencies**: Phases 3 (US2), 4 (US3), 6 (US5) must be complete — ViewSets must exist to add permission enforcement

### Implementation

- [x] T053 [US6] Add "export" to VALID_ACTIONS in Role model in backend/apps/auth/models.py (purchases and reports already in VALID_MODULES per R-008b)
- [x] T054 [P] [US6] Add permission enforcement to compras ViewSets in backend/apps/compras/views.py — SupplierViewSet (purchases.read/write/admin), PurchaseOrderViewSet (purchases.read/write/admin), GoodsReceiptViewSet (purchases.read/write)
- [x] T055 [P] [US6] Add permission enforcement to reportes ViewSets in backend/apps/reportes/views.py — ReportDefinitionViewSet (reports.read/write), SavedReportViewSet (reports.read), ExportJobViewSet (reports.read + reports.export for create)
- [x] T056 [US6] Update seed role definitions in backend/apps/core/management/commands/seed_data.py to include purchases and reports permission combinations
- [x] T057 [P] [US6] Write compras permission tests in tests/compras/test_permissions.py — read-only user, write user, admin user, no-permission user, cross-module isolation
- [x] T058 [P] [US6] Write reportes permission tests in tests/reportes/test_permissions.py — read-only user, export user, no-permission user
- [x] T059 [US6] GATE: Regression green

**Checkpoint**: All new endpoints enforce granular permissions. Unauthorized access returns 403.

---

## Phase 8: User Story 7 — Seed Data for New Modules (Priority: P3)

**Goal**: Provide sample data for purchases and reports modules, integrated with unified seed workflow

**Independent Test**: Run seed_compras + seed_reportes on clean DB, verify expected entities created. Run again, verify idempotent.

**Dependencies**: Phases 3 (US2), 4 (US3), 6 (US5) must be complete — seed data references PO, GR, and ReportDefinition models

### Implementation

- [x] T060 [P] [US7] Create seed_compras management command in backend/apps/compras/management/commands/seed_compras.py — create sample POs (DRAFT, CONFIRMED, PARTIAL_RECEIVED, RECEIVED states), PO items referencing existing seeded products, goods receipts with lines, use get_or_create for idempotency
- [x] T061 [P] [US7] Create seed_reportes management command in backend/apps/reportes/management/commands/seed_reportes.py — create sample ReportDefinitions (sales, stock, purchases types), use get_or_create for idempotency
- [x] T062 [US7] Update seed_all command in backend/apps/core/management/commands/seed_all.py to chain seed_compras (after seed_facturacion, needs products) and seed_reportes (last)
- [x] T063 [US7] Write seed command tests in tests/compras/test_seed_compras.py and tests/reportes/test_seed_reportes.py — verify idempotent execution (run twice, same counts), verify expected entity counts
- [x] T064 [US7] GATE: Regression green

**Checkpoint**: Seed data available. `seed_all` chain includes both new modules.

---

## Phase 9: Polish & Final Validation

**Purpose**: Cross-cutting concerns, admin interface, and final verification

- [x] T065 [P] Create PurchaseOrderAdmin (inline PurchaseOrderItemAdmin) + GoodsReceiptAdmin (inline GoodsReceiptLineAdmin) in backend/apps/compras/admin.py
- [x] T066 [P] Create ReportDefinitionAdmin, SavedReportAdmin, ExportJobAdmin in backend/apps/reportes/admin.py
- [x] T067 Full regression suite — verify 0 new failures across entire test suite
- [x] T068 Verify compras test count >= 60 and reportes test count >= 15
- [x] T069 Verify overall test coverage >= 78% (compras+reportes: 94%)
- [x] T070 Review all cross-module FK references — Product→compras.Supplier, GoodsReceiptLine→StockMovement, SavedReport→ReportDefinition, ExportJob→SavedReport
- [x] T071 Verify RLS policies active on all 7 new entity tables — created 0004_add_rls_policies (compras) and 0002_add_rls_policies (reportes)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)          → No dependencies — start immediately
Phase 2 (US1: Supplier)  → Depends on Phase 1 — BLOCKS Phases 3, 4, 5
Phase 3 (US2: PO)        → Depends on Phase 2
Phase 4 (US3: GR)        → Depends on Phase 3
Phase 5 (US4: Custom)    → Depends on Phase 3 (needs PO model)
Phase 6 (US5: Reportes)  → Depends on Phase 1 ONLY — can run parallel to Phases 2–5
Phase 7 (US6: Perms)     → Depends on Phases 3, 4, 6 (needs all ViewSets)
Phase 8 (US7: Seed)      → Depends on Phases 3, 4, 6 (needs all models)
Phase 9 (Polish)          → Depends on all phases
```

### Critical Path

```
Setup → US1 → US2 → US3 → US6 → US7 → Polish
                 ↘ US4 ↗ (can merge after US3)
Setup → US5 → US6 → US7 → Polish (parallel track)
```

### User Story Dependencies

| Story | Can Start After | Blocks |
|-------|----------------|--------|
| US1 (Supplier Migration) | Phase 1 | US2, US3, US4 |
| US2 (PO Lifecycle) | US1 | US3, US4, US6, US7 |
| US3 (Goods Receipt) | US2 | US6, US7 |
| US4 (Custom Fields) | US2 | — |
| US5 (Reportes) | Phase 1 | US6, US7 |
| US6 (Permissions) | US2 + US3 + US5 | US7 |
| US7 (Seed Data) | US2 + US3 + US5 | — |

### Within Each User Story

1. Models before serializers
2. Serializers before ViewSets
3. ViewSets before URL registration
4. Core implementation before tests
5. Tests verify the complete story increment
6. GATE regression before next phase

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (separate app skeletons)
- **Phase 3**: T022 and T023 can run in parallel (different test files)
- **Phase 4**: T033 and T034 can run in parallel (different test files)
- **Phase 6**: T049, T050, T051 can all run in parallel (different test files)
- **Phase 7**: T054+T055 in parallel, T057+T058 in parallel
- **Phase 8**: T060 and T061 can run in parallel (different seed commands)
- **Phase 9**: T065 and T066 can run in parallel (different admin files)
- **Cross-phase**: US5 (Phases 6) can run in parallel with US2–US4 after Phase 1

---

## Parallel Example: Phase 6 (US5 Reportes)

```bash
# Models can be built in sequence (same file), but tests run in parallel:
# Sequential: T040 → T041 → T042 → T043 → T044 → T045 → T046 → T047 → T048
# Then parallel tests:
Task: "Write report definition CRUD tests in tests/reportes/test_report_definition_crud.py"  # T049
Task: "Write saved report tests in tests/reportes/test_saved_report.py"                       # T050
Task: "Write export job tests in tests/reportes/test_export_job.py"                            # T051
```

## Parallel Example: Dual-Track Execution

```bash
# Track A (Compras): Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
# Track B (Reportes): Phase 1 → Phase 6 (starts after Phase 1, parallel to Track A)
# Merge: Phase 7 (needs both tracks) → Phase 8 → Phase 9
```

---

## Implementation Strategy

### MVP First (User Stories 1–3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: US1 Supplier Migration (RISKIEST — do first)
3. Complete Phase 3: US2 Purchase Order Lifecycle
4. Complete Phase 4: US3 Goods Receipt + Stock
5. **STOP and VALIDATE**: Full procurement loop works end-to-end
6. This delivers core business value: create PO → confirm → receive goods → stock updated

### Incremental Delivery

1. Setup + US1 → Foundation ready, suppliers in compras
2. + US2 → Purchase orders with state machine
3. + US3 → Full procurement loop with stock integration (MVP!)
4. + US4 → Custom fields on POs (tenant value-add)
5. + US5 → Reporting infrastructure skeleton
6. + US6 → Permission controls locked down
7. + US7 → Seed data for dev/demo
8. Polish → Admin, final validation, coverage

### Sequential Execution (Recommended for Single Agent)

Execute phases 1–9 in order. Each phase completes before the next begins. GATE regressions after each phase ensure stability. This is the safest approach and avoids merge conflicts.

---

## Notes

- [P] tasks = different files, no dependencies on in-progress tasks
- [US*] label maps task to specific user story for traceability
- All new models inherit TenantBoundModel (uuid PK, tenant FK, created_at, updated_at)
- All financial fields: DECIMAL(17,3) — never FLOAT/DOUBLE
- All ViewSets: cursor-based pagination, select_related/prefetch_related
- All list endpoints: filter backends matching contracts/ specs
- GoodsReceipt is append-only — no update/delete (immutable ledger)
- StockMovement type: use existing MovementType.PURCHASE (R-007)
- Supplier URL: clean break to /api/v1/compras/suppliers/ (R-003)
- Test runner: `bash scripts/run-tests-external.sh "{name}" "backend/venv-wsl/bin/python -m pytest {path} --tb=short -q"`
