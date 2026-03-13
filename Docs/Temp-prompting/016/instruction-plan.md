# Speckit Context: Backend Modules Solidification — PLAN Phase

> **Phase**: PLAN (implementation design, task breakdown, data model, API contracts, migration strategy). Uses the specification from `specs/016-backend-modules-solidification/spec.md` as input.

## Mission

Design an implementation plan for restructuring the GRAVITEA-ERP backend into an 8-module architecture. The plan must produce a `plan.md` with phased execution, task assignments, dependencies, validation criteria, and a clear sequential order. This is the largest backend feature since 001 — the plan must be surgical and sequential.

**Key outputs**:
- `plan.md` — phased implementation plan with complexity tracking
- `research.md` — research decisions on migration strategy, state machine design, JSONB expansion
- `data-model.md` — ERDs for new/modified entities (PurchaseOrder, GoodsReceipt, ReportDefinition, etc.)
- `contracts/` — OpenAPI YAML for new compras and reportes endpoints
- `quickstart.md` — execution guide for the implementation phase

## Team Architecture

### Agent Roster

| Agent | Role | Isolation | Purpose |
|-------|------|-----------|---------|
| **LEAD** | Orchestrator (main session) | — | Task management, plan authoring, cross-module coordination |
| **CODER** | `general-purpose` | worktree | Analyzes code, writes implementation, runs tests |
| **QA** | `quality-engineer` | — | Reviews code, validates tests, regression checking |

### Execution Model

    SEQUENTIAL — One task at a time

    For each task:
    1. LEAD assigns task with clear scope
    2. CODER analyzes relevant code → implements → writes tests
    3. QA reviews implementation → runs targeted + regression tests
    4. LEAD verifies green → moves to next task

**No parallel complex tasks.** The CODER implements one task, the QA validates it, and only then does the LEAD advance. This prevents the agent drift problem observed in previous features.

### Phase Dependencies

```
Phase 1: COMPRAS App Skeleton + Supplier Migration (RISKIEST — do first)
    │
Phase 2: PurchaseOrder + PurchaseOrderItem Models & API
    │
Phase 3: GoodsReceipt + StockMovement(PURCHASE_IN) Integration
    │
Phase 4: JSONB Custom Fields Expansion (PurchaseOrder.custom_data)
    │
Phase 5: REPORTES App Skeleton (Models + Basic CRUD)
    │
Phase 6: Permissions Vocabulary Expansion (compras.*, reportes.*)
    │
Phase 7: Seed Data (seed_compras, update seed_all)
    │
Phase 8: Final Regression + OpenAPI Documentation
```

Each phase completes fully (code + tests + regression green) before the next begins.

---

## Implementation Phases — Detailed Scope

### Phase 1: COMPRAS App Skeleton + Supplier Migration

**Risk level**: HIGHEST — this is the riskiest change in the entire feature.

**Tasks**:
1. Create `apps/compras/` Django app (models, views, serializers, urls, admin, apps.py)
2. Move Supplier model definition from `apps/inventario/models.py` to `apps/compras/models.py`
3. Create Django migration using `SeparateDatabaseAndState` to avoid data loss
4. Update `Product.supplier_id` FK target from `inventario.Supplier` to `compras.Supplier`
5. Update all imports referencing `inventario.Supplier` (views, serializers, admin, tests, seed commands)
6. Update URL routing: supplier endpoints move to `/api/v1/compras/suppliers/`
7. Update `TenantFieldDefinition.entity_type` — the `supplier` choice must work with new model location
8. Run full regression — ZERO new test failures required before proceeding

**Research topics for this phase**:
- R-001: Django `SeparateDatabaseAndState` migration pattern for model moves
- R-002: FK reference update strategy (direct alter vs. two-step migration)
- R-003: URL backward compatibility (redirect vs. clean break)

**Existing code references**:
- Current Supplier model: `backend/apps/inventario/models.py` (EncryptedCharField, blind indexes)
- Product FK to Supplier: `backend/apps/inventario/models.py` (Product.supplier)
- Supplier serializer: `backend/apps/inventario/serializers.py`
- Supplier views: `backend/apps/inventario/views.py`
- Supplier tests: `backend/tests/inventario/` (look for supplier-related test files)
- Seed command: `backend/apps/inventario/management/commands/seed_inventario.py`
- Custom fields: `backend/apps/core/serializers/customization.py` (CustomFieldsMixin, entity_type)
- TenantFieldDefinition: `backend/apps/core/models/` (entity_type choices)

### Phase 2: PurchaseOrder + PurchaseOrderItem Models & API

**Tasks**:
1. Create PurchaseOrder model (tenant-bound, FK to Supplier, state machine, custom_data JSONB)
2. Create PurchaseOrderItem model (FK to PurchaseOrder, FK to Product, quantity, unit_price)
3. Create serializers with nested items (follow SaleOrder/SaleOrderItem pattern)
4. Create ViewSets with CRUD + state transition actions
5. Create URL routing under `/api/v1/compras/purchase-orders/`
6. Write unit tests (model creation, validation, tenant isolation)
7. Write integration tests (CRUD, nested items, state transitions, error cases)
8. Run regression

**State machine design** (follow SaleOrder pattern):
```
PurchaseOrder states: DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED
                        │         │              │
                        └─────────┴──────────────┴──→ CANCELLED (from any non-received state)
```

**Pattern reference — SaleOrder state machine**:
- `backend/apps/ventas/models.py`: TextChoices enum, SALE_ORDER_TRANSITIONS dict, save() enforcement
- Transition logic: `save()` checks `self._state.adding` for new objects, otherwise validates `old_status → new_status` against transitions dict
- Mutable fields on CONFIRMED: `_MUTABLE_ON_CONFIRMED` whitelist pattern
- PurchaseOrder should follow the same pattern but with its own states and transitions

**Pattern reference — SaleOrderItem nested serializer**:
- `backend/apps/ventas/serializers.py`: Nested creation in SaleOrderSerializer.create()
- Items created inside transaction with parent FK
- Validation: product must exist, quantity > 0, etc.

### Phase 3: GoodsReceipt + StockMovement(PURCHASE_IN) Integration

**Tasks**:
1. Create GoodsReceipt model (FK to PurchaseOrder, received quantities per line, receipt_date)
2. Add `PURCHASE_IN` to StockMovement movement type choices (if not already present)
3. Create GoodsReceipt service that creates StockMovement(type=PURCHASE_IN) on receipt
4. Update PurchaseOrder state: receiving goods transitions PO to PARTIAL_RECEIVED or RECEIVED
5. Implement over-receipt rejection (FR-015: reject if received > ordered for any line)
6. Create serializers and ViewSet for GoodsReceipt
7. Write tests: receipt creation, stock update, over-receipt rejection, partial receipt
8. Run regression

**Pattern reference — StockMovement creation**:
- `backend/apps/inventario/services.py`: StockService with `@transaction.atomic`
- Types: SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT (PURCHASE may already exist)
- StockMovement is append-only (immutable ledger pattern) — never update or delete
- GoodsReceipt should call StockService (or equivalent) to create the movement

**Pattern reference — Service layer**:
- Stock movements are created via service calls, not directly in views
- Service wraps creation in `@transaction.atomic`
- Raises custom exceptions (InsufficientStockError, etc.) for business rule violations

### Phase 4: JSONB Custom Fields Expansion

**Tasks**:
1. Add `custom_data` JSONField to PurchaseOrder model (if not already in Phase 2)
2. Add `purchase_order` to `TenantFieldDefinition.entity_type` choices
3. Apply `CustomFieldsMixin` to PurchaseOrderSerializer
4. Write tests: custom field definition for PO, create PO with custom data, validate types
5. Run regression

**Pattern reference — CustomFieldsMixin**:
- Location: `backend/apps/core/serializers/customization.py` (lines 19-167)
- Requires `entity_type` class attribute on the serializer (e.g., `entity_type = "purchase_order"`)
- Provides: `validate_custom_data()`, `_apply_custom_defaults()` (create), `_merge_custom_data()` (update)
- Queries `TenantFieldDefinition` for the tenant + entity_type to get field schema
- Validates 6 types: text, integer, decimal, boolean, date, select
- `entity_type` choices defined in: `backend/apps/core/models/` (TenantFieldDefinition model)

### Phase 5: REPORTES App Skeleton

**Tasks**:
1. Create `apps/reportes/` Django app
2. Create ReportDefinition model (tenant-bound, type choices, parameters JSONB, filters JSONB, output_format)
3. Create SavedReport model (FK to ReportDefinition, result reference, execution metadata)
4. Create ExportJob model (FK to SavedReport, status, format, file_path)
5. Create serializers and ViewSets (basic CRUD only — no report generation logic)
6. Create URL routing under `/api/v1/reportes/`
7. Create read-only database views or querysets for BI tool connection
8. Write tests (15+ minimum: model creation, CRUD, tenant isolation, basic filters)
9. Run regression

**SCOPE BOUNDARY**: REPORTES is infrastructure skeleton ONLY. No report generators, no Looker Studio integration, no PDF/Excel generation, no scheduled reports. Those are future spec scope.

**Report types** (for ReportDefinition.report_type choices):
- `sales` — sales data (reads from ventas)
- `stock` — current inventory levels (reads from inventario)
- `purchases` — purchase orders (reads from compras)
- `fiscal` — fiscal data / comprobantes (reads from facturacion)
- `accounting_export` — data export for external accounting software

### Phase 6: Permissions Vocabulary Expansion

**Tasks**:
1. Add `compras` to VALID_MODULES in Role model
2. Add `reportes` to VALID_MODULES in Role model
3. Verify permission actions: `read`, `write`, `admin` for compras; `read`, `export` for reportes
4. Update seed roles to include new permissions
5. Write permission tests (access control for compras and reportes endpoints)
6. Run regression

**Pattern reference — Permission vocabulary**:
- Location: `backend/apps/auth/models.py` (Role model)
- `Role.permissions` is a JSONField containing list of `"{module}.{action}"` strings
- `Role.clean()` validates against `VALID_MODULES` and `VALID_ACTIONS` sets
- Example: `["inventario.read", "inventario.write", "compras.read", "compras.write"]`

### Phase 7: Seed Data

**Tasks**:
1. Create `seed_compras` management command (sample suppliers already exist from inventario seed — create POs, receipts)
2. Update `seed_all` to include `seed_compras` in the chain
3. Create sample ReportDefinition entries in seed (or separate `seed_reportes` command)
4. Write tests for seed commands (run without error, create expected records)
5. Run regression

**Pattern reference — Seed data**:
- Location: `backend/apps/inventario/management/commands/seed_inventario.py`
- Pattern: `BaseCommand` + `@transaction.atomic` + `set_current_tenant_id()` at start
- Data defined as module-level lists/dicts
- Creates records using `Model.objects.create()` or `get_or_create()`
- `seed_all` chain: `seed_data → seed_inventario → seed_ventas → seed_facturacion`

### Phase 8: Final Regression + OpenAPI Documentation

**Tasks**:
1. Run full test suite — verify 0 new failures
2. Generate/update OpenAPI YAML for compras endpoints
3. Generate/update OpenAPI YAML for reportes endpoints
4. Verify minimum test counts: 60+ for compras, 15+ for reportes
5. Verify coverage maintains or improves from current ~78%
6. Final review of all cross-module FK references

---

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Alternatives |
|----|-------|----------------|-------------|
| R-001 | Supplier model move migration strategy | `SeparateDatabaseAndState` vs `AlterModelTable` vs manual SQL | Standard Django practice for model moves |
| R-002 | Product.supplier_id FK update during migration | Same migration as model move vs separate migration | Transaction safety, rollback strategy |
| R-003 | Supplier URL backward compatibility | Clean break (`/compras/suppliers/`) vs redirect from old URL | MVP: clean break is simpler |
| R-004 | PurchaseOrder state machine: INVOICED state | Include INVOICED state now (future-proofing) vs defer to supplier invoicing spec | Spec says defer — INVOICED is not in scope |
| R-005 | GoodsReceipt granularity | One receipt per PO vs multiple partial receipts per PO | Multiple partial receipts (spec has PARTIAL_RECEIVED state) |
| R-006 | REPORTES read-only views | Database VIEWs vs Django querysets vs both | Start with Django querysets, add DB views if needed for Looker |
| R-007 | StockMovement PURCHASE_IN type | Already exists in codebase vs needs adding | Check `StockMovement.MovementType` choices |

---

## Data Model Design (for data-model.md)

### New Entities

#### PurchaseOrder (apps/compras/)
- `id` — UUID (TenantBoundModel standard)
- `tenant` — FK to Tenant (inherited from TenantBoundModel)
- `supplier` — FK to compras.Supplier
- `order_number` — CharField, unique per tenant
- `status` — CharField with TextChoices (DRAFT, CONFIRMED, PARTIAL_RECEIVED, RECEIVED, CANCELLED)
- `order_date` — DateField
- `expected_delivery_date` — DateField (nullable)
- `notes` — TextField (nullable)
- `custom_data` — JSONField (CustomFieldsMixin)
- `total_amount` — DecimalField (calculated)
- `created_at`, `updated_at` — DateTimeField (auto)

#### PurchaseOrderItem (apps/compras/)
- `id` — UUID
- `purchase_order` — FK to PurchaseOrder (CASCADE)
- `product` — FK to inventario.Product
- `quantity` — DecimalField
- `unit_price` — DecimalField
- `line_total` — DecimalField (calculated)
- `received_quantity` — DecimalField (default 0, updated by GoodsReceipt)

#### GoodsReceipt (apps/compras/)
- `id` — UUID (TenantBoundModel)
- `tenant` — FK to Tenant
- `purchase_order` — FK to PurchaseOrder
- `receipt_number` — CharField, unique per tenant
- `receipt_date` — DateField
- `received_by` — FK to AppUser (nullable)
- `notes` — TextField (nullable)
- `created_at` — DateTimeField (auto)

#### GoodsReceiptItem (apps/compras/) — if line-level tracking needed
- `id` — UUID
- `goods_receipt` — FK to GoodsReceipt (CASCADE)
- `purchase_order_item` — FK to PurchaseOrderItem
- `quantity_received` — DecimalField
- NOTE: Research decision R-005 determines if this model is needed

#### ReportDefinition (apps/reportes/)
- `id` — UUID (TenantBoundModel)
- `tenant` — FK to Tenant
- `name` — CharField
- `report_type` — CharField with choices (sales, stock, purchases, fiscal, accounting_export)
- `parameters` — JSONField (configuration for the report)
- `filters` — JSONField (filter criteria)
- `output_format` — CharField with choices (PDF, Excel, CSV)
- `is_active` — BooleanField
- `created_at`, `updated_at` — DateTimeField

#### SavedReport (apps/reportes/)
- `id` — UUID (TenantBoundModel)
- `tenant` — FK to Tenant
- `report_definition` — FK to ReportDefinition
- `generated_at` — DateTimeField
- `result_metadata` — JSONField (execution info, row count, etc.)
- `file_reference` — CharField (path or blob key, nullable)
- `status` — CharField (PENDING, COMPLETED, FAILED)

#### ExportJob (apps/reportes/)
- `id` — UUID (TenantBoundModel)
- `tenant` — FK to Tenant
- `saved_report` — FK to SavedReport
- `export_format` — CharField (PDF, Excel, CSV)
- `status` — CharField (PENDING, PROCESSING, COMPLETED, FAILED)
- `file_path` — CharField (nullable)
- `created_at`, `completed_at` — DateTimeField

### Modified Entities

#### Supplier (MOVED from inventario to compras)
- No field changes — only the app ownership changes
- All encrypted fields (tax_id, contact_info, email, address) + blind indexes preserved
- `custom_data` JSONField preserved (entity_type remains `supplier`)

#### Product (inventario — FK update)
- `supplier` FK target changes: `inventario.Supplier` → `compras.Supplier`
- No other field changes

#### StockMovement (inventario — new type)
- Add `PURCHASE_IN` to MovementType choices (if not already present)
- No other field changes

#### TenantFieldDefinition (core — new entity_type)
- Add `purchase_order` to `entity_type` choices

#### Role (auth — new permissions)
- Add `compras` and `reportes` to VALID_MODULES set
- Add `export` to VALID_ACTIONS set (for `reportes.export`)

### Cross-Module FK Map (After Changes)

| Source | Target | FK Field | Change |
|--------|--------|----------|--------|
| `PurchaseOrder` (compras) | `Supplier` (compras) | `supplier_id` | **NEW** |
| `PurchaseOrderItem` (compras) | `PurchaseOrder` (compras) | `purchase_order_id` | **NEW** |
| `PurchaseOrderItem` (compras) | `Product` (inventario) | `product_id` | **NEW** |
| `GoodsReceipt` (compras) | `PurchaseOrder` (compras) | `purchase_order_id` | **NEW** |
| `Product` (inventario) | `Supplier` (compras) | `supplier_id` | **CHANGED** target |
| `SavedReport` (reportes) | `ReportDefinition` (reportes) | `report_definition_id` | **NEW** |
| `ExportJob` (reportes) | `SavedReport` (reportes) | `saved_report_id` | **NEW** |
| _All existing FKs_ | _unchanged_ | — | No change |

---

## API Contracts (for contracts/)

### COMPRAS Endpoints

```
/api/v1/compras/suppliers/           GET, POST
/api/v1/compras/suppliers/{id}/      GET, PUT, PATCH, DELETE
/api/v1/compras/purchase-orders/     GET, POST
/api/v1/compras/purchase-orders/{id}/              GET, PUT, PATCH, DELETE
/api/v1/compras/purchase-orders/{id}/confirm/      POST (transition to CONFIRMED)
/api/v1/compras/purchase-orders/{id}/cancel/       POST (transition to CANCELLED)
/api/v1/compras/purchase-orders/{id}/goods-receipts/   GET, POST (nested)
/api/v1/compras/goods-receipts/      GET (list all receipts)
/api/v1/compras/goods-receipts/{id}/ GET
```

### REPORTES Endpoints

```
/api/v1/reportes/definitions/        GET, POST
/api/v1/reportes/definitions/{id}/   GET, PUT, PATCH, DELETE
/api/v1/reportes/saved-reports/      GET, POST
/api/v1/reportes/saved-reports/{id}/ GET, DELETE
/api/v1/reportes/export-jobs/        GET, POST
/api/v1/reportes/export-jobs/{id}/   GET
```

---

## Existing Codebase Patterns (Mandatory to Follow)

### 1. TenantBoundModel
All new models MUST inherit from `TenantBoundModel` (in `apps/core/models/`). This provides:
- `tenant` FK (auto-set via middleware)
- `TenantBoundManager` as default manager (filters by current tenant)
- UUID primary keys
- `created_at` / `updated_at` timestamps

### 2. State Machine Pattern
Follow the SaleOrder pattern in `apps/ventas/models.py`:
- Define states as `TextChoices` enum
- Define transitions dict: `{old_status: [allowed_new_statuses]}`
- Enforce transitions in `save()` method
- Whitelist mutable fields per state

### 3. Immutable Ledger Pattern
StockMovement and GoodsReceipt follow append-only patterns:
- No `update` or `delete` operations
- Corrections create new reversal entries
- All changes are auditable via created_at

### 4. CustomFieldsMixin
Apply to serializers for entities that support custom_data:
- Set `entity_type` class attribute
- Mixin provides validate/create/update hooks
- Located in `apps/core/serializers/customization.py`

### 5. Encrypted Fields
Supplier uses `EncryptedCharField` / `EncryptedTextField` with blind index hashes:
- `tax_id_encrypted` + `tax_id_hash` (for search)
- `email_encrypted` + `email_hash`
- Pattern in `apps/core/encryption/`

### 6. Service Layer
Business logic (especially stock movements) lives in service classes, not views:
- `StockService` in `apps/inventario/services.py`
- Services use `@transaction.atomic`
- Views call services, services call models

### 7. Permission Vocabulary
- `Role.permissions` JSONField with `"{module}.{action}"` format
- Validated in `Role.clean()` against `VALID_MODULES` and `VALID_ACTIONS` sets
- Add new modules/actions to these sets

### 8. Seed Data Pattern
- Management commands extending `BaseCommand`
- `@transaction.atomic` decorator
- `set_current_tenant_id()` before creating records
- Idempotent (use `get_or_create` where appropriate)

---

## Testing Standards

- **Every new model**: Unit tests (creation, validation, tenant isolation, str representation)
- **Every new endpoint**: Integration tests (CRUD, permissions, error cases, edge cases)
- **Every migration**: Full regression run
- **Supplier migration**: Special attention — verify all existing supplier tests pass at new location
- **Minimum counts**: 60 new tests for compras, 15 for reportes infrastructure
- **Coverage target**: Maintain or improve from current ~78%
- **Test execution**: Use `scripts/run-tests-external.sh` for token optimization
- **Pattern**: Follow existing test organization in `backend/tests/`

---

## Constraints

1. **Sequential execution**: One phase at a time, fully tested before proceeding
2. **Migration safety**: Supplier move uses `SeparateDatabaseAndState` — no data loss
3. **Backward compatibility**: If supplier URL changes, decide in R-003 (redirect or clean break)
4. **Tenant isolation**: All new models inherit TenantBoundModel with TenantBoundManager
5. **REPORTES is skeleton only**: No report generators, no Looker Studio integration, no scheduled reports
6. **No frontend**: This spec is backend-only — no React/Next.js components
7. **No GCP deployment**: Development environment only (Docker Compose)
8. **No CI/CD**: Manual test execution via scripts
9. **Existing tests must pass**: 0 regressions allowed from supplier migration or any other change

## Success Criteria (from spec)

1. `apps/compras/` exists with Supplier (migrated), PurchaseOrder, PurchaseOrderItem, GoodsReceipt
2. `apps/reportes/` exists with ReportDefinition, SavedReport, ExportJob (infrastructure skeleton)
3. Supplier migration is safe — no data loss, all existing FK references intact
4. All new models inherit TenantBoundModel with proper tenant isolation
5. PurchaseOrder state machine works (DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED)
6. GoodsReceipt creates StockMovement(type=PURCHASE_IN) correctly
7. PurchaseOrder.custom_data works with CustomFieldsMixin
8. REPORTES has basic CRUD endpoints for ReportDefinition and SavedReport
9. All existing tests continue to pass (0 regressions)
10. 60+ new tests for compras, 15+ for reportes
11. REST API endpoints documented with OpenAPI YAML
12. Seed data exists for both new modules
13. Permission vocabulary includes compras.* and reportes.* actions

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Feature spec | Primary input — user stories, FRs, SCs | `specs/016-backend-modules-solidification/spec.md` |
| Instruction context | Architecture decisions, system overview | `Docs/Temp-prompting/016/instruction-specify.md` |
| 014 spec | JSONB pattern reference (most recent feature) | `specs/014-tenant-customization/spec.md` |
| 001 spec | Largest backend feature (ventas + facturacion pattern) | `specs/001-sal-invo-inve-backend/spec.md` |
| Current inventario models | Supplier source code (to be migrated) | `backend/apps/inventario/models.py` |
| Current ventas models | SaleOrder pattern reference | `backend/apps/ventas/models.py` |
| Core models | TenantBoundModel, TenantFieldDefinition | `backend/apps/core/models/` |
| CustomFieldsMixin | JSONB validation mixin | `backend/apps/core/serializers/customization.py` |
| StockService | Stock movement creation pattern | `backend/apps/inventario/services.py` |
| Auth models | Role, permission vocabulary | `backend/apps/auth/models.py` |
| Seed commands | Seed data patterns | `backend/apps/inventario/management/commands/` |
| Plan template | Output format reference | `.specify/templates/plan-template.md` |
