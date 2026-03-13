# Speckit Context: Backend Modules Solidification

> **Phase**: SPECIFY (module architecture, scope definitions, entity ownership, JSONB strategy, migration plan). Implementation planning follows in a separate `speckit.plan` run.

## Mission Statement

Produce a specification for restructuring the GRAVITEA-ERP backend into a well-defined 8-module architecture. This spec covers CODE changes only: creating new Django apps (`compras`, `reportes`), migrating the `Supplier` model from `inventario` to `compras`, building the purchase workflow (PurchaseOrder, GoodsReceipt), establishing the reporting module infrastructure (skeleton + Looker Studio connection point), expanding JSONB customization to new entities, and ensuring all existing tests continue to pass.

This is a MASSIVE backend feature — the largest since Feature 001. It touches every existing module either directly (inventario loses Supplier) or indirectly (ventas, facturacion gain new cross-module relationships). The specification must be surgical: each change has clear scope, each migration has rollback strategy, and the implementation must be sequential (one task at a time, tested before moving to the next).

**IMPORTANT — REPORTES scope**: REPORTES is deliberately LIMITED to infrastructure skeleton in this spec. The full BI capabilities (embedded Looker Studio per tenant, custom report generators, advanced analytics) will be developed in a dedicated future spec once all core transactional modules are solid. This spec only establishes the module's foundation: models, basic CRUD endpoints, and the data access layer that Looker Studio (or any BI tool) can connect to.

## Why This Matters Now

The backend has 6 complete modules (AUTH, CORE, INVENTARIO, VENTAS, FACTURACION, SYNC) but their boundaries have organic pain points:

1. **Supplier is misplaced**: `Supplier` model lives in `apps/inventario/` but semantically owns the purchase workflow. When COMPRAS is built, it needs to own Supplier.
2. **COMPRAS doesn't exist**: The purchase workflow (PO, goods receipt, supplier invoicing) is MVP-required per the Roadmap. Only the Supplier model exists.
3. **REPORTES doesn't exist**: Reports module infrastructure is needed. Zero code, zero models, zero endpoints. Full BI capabilities (Looker Studio, custom reports) are future scope — this spec only establishes the module skeleton.
4. **Module scope is informal**: No document strictly defines what each module owns, what it may access, and what JSONB customization it supports.
5. **JSONB expansion needed**: Feature 014 added custom fields to 4 entities (product, customer, supplier, sale_order). New entities in COMPRAS need the same treatment.

## Architecture Decisions (FINAL — Do Not Re-Debate)

These decisions were made by the project owner and are not negotiable in the spec:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Supplier ownership** | Moves to `apps/compras/` | Supplier is a purchasing party. PurchaseOrder will FK to it. |
| **Customer ownership** | Stays in `apps/ventas/` | Customer has ARCA fiscal fields (condicion_iva, doc_tipo) that directly determine invoice type A/B/C. Tight fiscal coupling. |
| **No "parties" module** | No extraction of Customer+Supplier into shared module | Over-engineering for MVP. The dual-role party scenario (customer=supplier) is post-MVP. |
| **Spec scope** | Code only | Blueprint doc updates are a separate follow-up spec. |
| **Implementation methodology** | Sequential, one task at a time | No parallel complex agent tasks. Each task: analyze → code → test → verify → next. |
| **Feature number** | 016 | Next sequential after 015. |

## System Overview (Actual State — February 2026)

### Current Backend Module Map

| Module | Django App | Models | Status |
|--------|-----------|--------|--------|
| **CORE** | `apps/core/` | Tenant, Branch, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate | Complete |
| **AUTH** | `apps/auth/` | AppUser, Role | Complete |
| **INVENTARIO** | `apps/inventario/` | Product, ProductCategory, PriceList, PriceListItem, ProductPriceHistory, ProductCostHistory, StockMovement, StockSnapshot, **Supplier** (misplaced) | Complete |
| **VENTAS** | `apps/ventas/` | Customer, SaleOrder, SaleOrderItem | Complete |
| **FACTURACION** | `apps/facturacion/` | ARCACredential, PuntoDeVenta, Comprobante, AlicIva, Tributo, CbteAsoc, CAEA | Complete |
| **SYNC** | `apps/sync/` | SyncSession, PendingOperation | Complete |
| **COMPRAS** | *does not exist* | — | Not started (Supplier lives in inventario) |
| **REPORTES** | *does not exist* | — | Not started |

### Current Quality Metrics

| Metric | Value |
|--------|-------|
| Passing tests | 2,202+ |
| Failed (pre-existing) | 25 (Docker/deployment) |
| Test coverage | ~78% |
| API endpoints | 100+ |
| Django migrations | 23+ |
| OpenAPI spec files | 6 YAML |

### Cross-Module Foreign Keys (Current)

| Source | Target | FK Field |
|--------|--------|----------|
| `StockMovement` (inventario) | `SaleOrder` (ventas) | `sale_order_id` |
| `StockMovement` (inventario) | `Comprobante` (facturacion) | `comprobante_id` |
| `Comprobante` (facturacion) | `SaleOrder` (ventas) | `sale_order_id` (OneToOne) |
| `Comprobante` (facturacion) | `Customer` (ventas) | `customer_id` |
| `SaleOrderItem` (ventas) | `Product` (inventario) | `product_id` |
| `Product` (inventario) | `Supplier` (inventario) | `supplier_id` |
| `PuntoDeVenta` (facturacion) | `Branch` (core) | `branch_id` |

### JSONB Customization (Feature 014)

**Framework**: `TenantFieldDefinition` in core defines per-tenant custom fields. `CustomFieldsMixin` in DRF validates `custom_data` JSONB column against definitions.

| Entity | `custom_data` Column | `entity_type` Choice | Status |
|--------|---------------------|---------------------|--------|
| Product | `Product.custom_data` | `product` | Implemented |
| Customer | `Customer.custom_data` | `customer` | Implemented |
| Supplier | `Supplier.custom_data` | `supplier` | Implemented |
| SaleOrder | `SaleOrder.custom_data` | `sale_order` | Implemented |
| PurchaseOrder | — | — | **Needs adding** |

**Field types supported**: text, integer, decimal, boolean, date, select (with options JSONB).

---

## Target Architecture (8 Modules)

### Module 1: CORE — Infrastructure & Customization Framework
- **Owns**: Tenant, Branch, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate
- **Provides**: TenantBoundModel, TenantBoundManager, encryption, middleware, observability, CustomFieldsMixin
- **Changes needed**: Expand `entity_type` choices to include `purchase_order`
- **JSONB**: `TenantFieldDef.options`, `TenantModuleConfig.settings`, `BusinessTemplate.modules`+`.field_definitions`

### Module 2: AUTH — Authentication & Authorization
- **Owns**: AppUser, Role
- **Changes needed**: Add `compras.read`, `compras.write`, `compras.admin`, `reportes.read`, `reportes.export` to permission vocabulary
- **JSONB**: `Role.permissions` (array of `{module}.{action}`)
- **No custom_data**: Security boundary

### Module 3: INVENTARIO — Products, Stock & Pricing
- **Owns**: Product, ProductCategory, PriceList, PriceListItem, ProductPriceHistory, ProductCostHistory, StockMovement, StockSnapshot
- **LOSES**: Supplier (→ compras)
- **Changes needed**: `Product.supplier_id` FK target changes from `inventario.Supplier` to `compras.Supplier`. StockMovement gains new movement type `PURCHASE_IN` (from goods receipt).
- **JSONB**: `Product.custom_data`, `Product.ml_tags`
- **Immutable**: StockMovement (append-only ledger)

### Module 4: VENTAS — Sales & Customers
- **Owns**: Customer, SaleOrder, SaleOrderItem
- **Changes needed**: None structural. May need adjustment if Comprobante gains new FK relationships.
- **JSONB**: `Customer.custom_data`, `SaleOrder.custom_data`
- **State machine**: SaleOrder (DRAFT → CONFIRMED → INVOICED)

### Module 5: COMPRAS — Purchases & Suppliers (NEW)
- **Owns**: Supplier (moved from inventario), PurchaseOrder, PurchaseOrderItem, GoodsReceipt
- **New models**:
  - `PurchaseOrder`: tenant-bound, FK to Supplier, state machine (DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED → INVOICED)
  - `PurchaseOrderItem`: FK to PurchaseOrder, FK to Product (inventario), quantity, unit_price
  - `GoodsReceipt`: FK to PurchaseOrder, records actual received quantities, creates StockMovement(type=PURCHASE_IN)
- **JSONB**: `Supplier.custom_data` (existing), `PurchaseOrder.custom_data` (new)
- **Encryption**: Supplier PII fields remain encrypted (AES-256-GCM + BlindIndex)
- **Scope boundary**: Owns the buy-side workflow. GoodsReceipt creates StockMovement in inventario via service call.

### Module 6: FACTURACION — ARCA Electronic Invoicing
- **Owns**: ARCACredential, PuntoDeVenta, Comprobante, AlicIva, Tributo, CbteAsoc, CAEA
- **Changes needed**: Comprobante may need FK to PurchaseOrder for supplier invoices (Factura C proveedor). This is a design decision for the spec.
- **JSONB**: None (fiscal data is strictly typed)
- **Immutable**: Comprobante (after AUTORIZADO)

### Module 7: REPORTES — Reporting Infrastructure Skeleton (NEW)
- **Owns**: ReportDefinition, SavedReport, ExportJob
- **New models**:
  - `ReportDefinition`: tenant-bound, defines report type (sales, stock, purchases, fiscal, accounting_export), parameters JSONB, filters JSONB, output_format choices
  - `SavedReport`: FK to ReportDefinition, stores generated report reference (file path or blob key), execution metadata
  - `ExportJob`: FK to SavedReport, tracks export status and format (PDF, Excel, CSV), file path
- **JSONB**: `ReportDefinition.parameters`, `ReportDefinition.filters`, `SavedReport.result_metadata`
- **Scope boundary**: Read-only against all other modules. Does NOT write business data. Infrastructure only — no report generators in this spec.
- **BI strategy (future, NOT this spec)**:
  - Primary BI: Embedded Looker Studio instance per tenant (connects to read-replica or views)
  - Custom reports: PDF, CSV, Excel, Python-generated infographics
  - Scheduled reports: Cron-like automated generation and delivery
  - All of the above will be developed in a dedicated future spec
- **What THIS spec delivers**:
  - Django app skeleton (`apps/reportes/`)
  - Models with proper tenant isolation
  - Basic CRUD endpoints for ReportDefinition and SavedReport
  - Database views or read-only querysets that Looker Studio (or any BI tool) can connect to
  - Permission vocabulary (`reportes.read`, `reportes.export`)
  - Seed data with sample ReportDefinition entries

### Module 8: SYNC — Offline Synchronization
- **Owns**: SyncSession, PendingOperation
- **Changes needed**: Sync entity registry may need to include new COMPRAS entities (Supplier at new path, PurchaseOrder)
- **JSONB**: `PendingOperation.payload`, `SyncSession.sync_vector`

---

## Migration Strategy: Supplier Move (inventario → compras)

This is the riskiest change in the spec. The migration must:

1. **Create** `apps/compras/` app with models, views, serializers, urls
2. **Move** the Supplier model definition from `apps/inventario/models.py` to `apps/compras/models.py`
3. **Update** Django migration to use `SeparateDatabaseAndState` or `migrations.AlterModelTable` to avoid data loss
4. **Update** `Product.supplier_id` FK to point to `compras.Supplier` instead of `inventario.Supplier`
5. **Update** all imports: views, serializers, admin, tests that reference `inventario.Supplier`
6. **Update** URL routing: `/api/v1/inventario/suppliers/` → `/api/v1/compras/suppliers/`
7. **Update** `TenantFieldDefinition.entity_type` — the `supplier` choice must work with the new model location
8. **Verify**: All existing Supplier tests pass at the new location
9. **Verify**: No broken FK references in database

**Risk mitigation**: The migration should be the FIRST phase, isolated and tested before building PurchaseOrder or any new models.

---

## Implementation Methodology

The user explicitly requires a systematic approach:

    For each task in the spec:
    1. ANALYZE: Read the relevant source code, understand current state
    2. CODE: Write or modify code (models, serializers, views, urls, services)
    3. TEST: Write tests for the new/changed code
    4. EXECUTE: Run the test suite (targeted + regression)
    5. VERIFY: Confirm tests pass, no regressions
    6. NEXT: Move to the next task only after verification

**No parallel complex tasks.** Agents may be used in a team (LEAD + CODER + QA), but only one task is active at a time. The CODER implements, the QA tests, the LEAD coordinates. This prevents the agent drift problem observed in previous features.

**Testing standards**:
- Every new model gets unit tests (creation, validation, tenant isolation)
- Every new endpoint gets integration tests (CRUD, permissions, error cases)
- Every migration gets a regression run against the full suite
- Use `scripts/run-tests-external.sh` for test execution (token optimization)
- Target: 0 new test failures, maintain or improve coverage

---

## Constraints and Boundaries

### What This Spec Covers

- Creating `apps/compras/` Django app (Supplier migration + PurchaseOrder workflow)
- Creating `apps/reportes/` Django app (infrastructure skeleton for future BI)
- Moving Supplier model from inventario to compras (with safe migration)
- New REST API endpoints for compras and reportes
- JSONB custom fields expansion (PurchaseOrder.custom_data)
- Permission vocabulary expansion (compras.*, reportes.*)
- New StockMovement type (PURCHASE_IN) for goods receipt
- Comprehensive test suite for all new code
- Seed data for new modules (seed_compras, update seed_all)

### What This Spec Does NOT Cover

- Blueprint document updates (separate follow-up spec)
- Frontend components for compras/reportes (separate feature)
- Electron desktop app
- GCP deployment
- CI/CD pipeline
- Supplier invoicing via ARCA (Factura C proveedor) — post-MVP unless trivially added
- Full reporting engine / report generators (future spec — this spec is infrastructure only)
- Embedded Looker Studio integration (future spec — requires GCP deployment first)
- Custom report templates, PDF/Excel generation logic (future spec)
- ScheduledReport model and cron execution (future spec)
- Customer extraction to parties module (rejected — stays in ventas)

### Key Principles

1. **One module at a time**: Complete COMPRAS fully (including tests) before starting REPORTES
2. **Migration safety**: Supplier move uses Django's `SeparateDatabaseAndState` to avoid data loss
3. **Backward compatibility**: Existing API consumers should not break. If URL changes, add redirect or versioning.
4. **Tenant isolation**: All new models inherit TenantBoundModel. All new managers use TenantBoundManager.
5. **Immutable patterns**: GoodsReceipt creates StockMovement(type=PURCHASE_IN) — append-only, same pattern as sales.
6. **JSONB consistency**: New entities follow the same CustomFieldsMixin pattern from Feature 014.
7. **Test-driven verification**: Each task is complete only when tests pass and regression is green.

---

## Success Criteria

1. `apps/compras/` exists with Supplier (migrated), PurchaseOrder, PurchaseOrderItem, GoodsReceipt models
2. `apps/reportes/` exists with ReportDefinition, SavedReport, ExportJob models (infrastructure skeleton)
3. Supplier migration is safe — no data loss, all existing FK references intact
4. All new models inherit TenantBoundModel with proper tenant isolation
5. PurchaseOrder state machine works (DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED)
6. GoodsReceipt creates StockMovement(type=PURCHASE_IN) correctly
7. PurchaseOrder.custom_data works with CustomFieldsMixin
8. REPORTES has basic CRUD endpoints for ReportDefinition and SavedReport
9. REPORTES provides read-only database views or querysets suitable for external BI tool connection (Looker Studio)
10. All existing tests continue to pass (0 regressions from Supplier migration)
11. New test count: minimum 60 new tests for compras, minimum 15 for reportes infrastructure
12. REST API endpoints for compras and reportes are documented with OpenAPI
13. Seed data exists for both new modules
14. Permission vocabulary includes compras.* and reportes.* actions

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| CLAUDE.md | Project overview, skill registry | `CLAUDE.md` |
| 014 Spec | Most recent feature (tenant customization — JSONB pattern reference) | `specs/014-tenant-customization/spec.md` |
| 001 Spec | Largest backend feature (ventas + facturacion — workflow pattern reference) | `specs/001-sal-invo-inve-backend/spec.md` |
| Current inventario models | Supplier source code (to be migrated) | `backend/apps/inventario/models.py` |
| Current ventas models | Customer + SaleOrder (pattern reference for PurchaseOrder) | `backend/apps/ventas/models.py` |
| Current core models | TenantBoundModel, TenantFieldDefinition | `backend/apps/core/models/` |
| CustomFieldsMixin | JSONB validation mixin | `backend/apps/core/serializers/` |
| Docker Compose | Service configuration | `docker-compose.yml` |
| Roadmap | MVP target and remaining items | `Docs/Project Blueprint/Roadmap.md` |
| Data Model doc | Current ERDs (needs updating after this feature) | `Docs/Project Blueprint/Data Model & Domain Model.md` |

---

## Phase Boundary

This specification covers **WHAT** modules to build, **WHY** they matter, and **WHAT** the acceptance criteria are. It does NOT cover:

- HOW to organize the implementation work (that's `speckit.plan`)
- WHICH tasks to create and in what order (that's `speckit.tasks`)
- WHO executes each task (that's `speckit.implement`)
- HOW to update Blueprint docs (that's a separate follow-up spec)

The specify agent should use this context to produce a rigorous spec.md with testable user stories, detailed functional requirements, and measurable success criteria — all focused on the backend code changes.
