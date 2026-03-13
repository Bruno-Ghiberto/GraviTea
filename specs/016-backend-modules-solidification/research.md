# Research: Backend Modules Solidification

**Branch**: `016-backend-modules-solidification` | **Date**: 2026-02-24 | **Spec**: [spec.md](./spec.md)

## R-001: Django SeparateDatabaseAndState Migration Pattern

**Decision**: Use `SeparateDatabaseAndState` with a 3-step migration approach.

**Rationale**: Standard Django pattern for moving models between apps. The database table stays in place (no data copy needed) — only Django's internal state tracking changes. The actual database table `inventario_supplier` can be renamed to `compras_supplier` using `AlterModelTable`, or left with the original name using `db_table` meta option.

**Alternatives considered**:
- **AlterModelTable only**: Simpler but doesn't handle FK references across apps cleanly
- **Manual SQL + RunPython**: Too low-level, error-prone, hard to reverse
- **Copy data + delete old**: Unnecessary data duplication, risk of data loss during transition

**Implementation approach**:
1. Create `compras` app migration with `SeparateDatabaseAndState`: state_operations creates the model in Django's state, database_operations is empty (table already exists as `inventario_supplier`)
2. Set `db_table = "inventario_supplier"` on Supplier in compras OR use `AlterModelTable` to rename
3. Create `inventario` app migration with `SeparateDatabaseAndState`: state_operations deletes model from inventario state, database_operations is empty
4. Separate migration to update Product FK reference

## R-002: Product.supplier_id FK Update Strategy

**Decision**: Update FK target to `"compras.Supplier"` in the same migration batch as the model move.

**Rationale**: Product.supplier currently uses `models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)`. Since the database column (`supplier_id`) and table don't change (just Django's internal state tracking), the FK update is a state-only operation. Doing it in the same migration batch ensures atomicity.

**Alternatives considered**:
- **Separate migration after model move**: Adds risk of intermediate state where FK target is invalid
- **Two-phase with data migration**: Unnecessary — column stays the same, only Django state changes

## R-003: Supplier URL Backward Compatibility

**Decision**: Clean break — move to `/api/v1/compras/suppliers/`, no redirect from old URL.

**Rationale**: This is an internal development environment with no external API consumers. The frontend prototype is under active development and can be updated. All 3 test files referencing supplier URLs will be updated. Clean break avoids the complexity of maintaining redirect middleware.

**Alternatives considered**:
- **Redirect from old URL**: Adds complexity (URL conf, middleware) for zero benefit in MVP
- **Keep both URLs**: Semantic confusion — suppliers are procurement entities, not inventory

**Files requiring URL update**: `tests/performance/test_n_plus_one.py`, `tests/inventario/test_inventory_api.py`, `tests/integration/test_custom_fields_e2e.py`

## R-004: PurchaseOrder INVOICED State

**Decision**: Defer INVOICED state — not included in MVP.

**Rationale**: The spec explicitly defines PO states as DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED. Supplier invoicing (Factura C proveedor) is a separate future feature. Purchase orders don't generate ARCA invoices — supplier invoices are inbound documents that arrive asynchronously. Adding INVOICED now would be dead code.

**Alternatives considered**:
- **Include INVOICED state now**: Future-proofing, but violates YAGNI — the state would have no transition logic, no triggers, no tests

**MVP State Machine**:
```
DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED (terminal)
  │         │              │
  └─────────┴──────────────┴──→ CANCELLED (terminal)
```

## R-005: GoodsReceipt Granularity

**Decision**: GoodsReceipt header + GoodsReceiptLine items (per-line tracking).

**Rationale**: Spec acceptance scenario US3-2 explicitly requires "40 of 100 received" per line. Real goods receipts list multiple line items with different quantities. Per-line tracking enables variance detection and individual stock movement creation.

**Alternatives considered**:
- **Single quantity per GoodsReceipt**: Cannot track which lines were partially received
- **No GoodsReceiptLine model**: Would require embedding quantities in JSONB — loses FK integrity

**Data model**: GoodsReceipt (header: PO reference, date, notes) → GoodsReceiptLine (per PO line: quantity_received) → StockMovement (one per line)

## R-006: REPORTES Read-Only Views

**Decision**: Django QuerySets with TenantBoundManager (no PostgreSQL VIEWs in MVP).

**Rationale**: No existing VIEW patterns in the codebase. QuerySets provide automatic tenant isolation via TenantBoundManager, standard testing with pytest-django, and no schema migration per new report type. PostgreSQL VIEWs can be added later if Looker Studio needs direct DB connection.

**Alternatives considered**:
- **PostgreSQL VIEWs**: Better for direct BI tool connection, but adds SQL maintenance burden and tenant isolation complexity
- **Both QuerySets + VIEWs**: Over-engineering for skeleton module — deferred until GCP deployment

## R-007: StockMovement PURCHASE Type

**Decision**: Use existing `PURCHASE` type — no new type needed.

**Rationale**: `StockMovement.MovementType` already includes `PURCHASE = "PURCHASE"`. The PostgreSQL ENUM `stock_movement_type_enum` also includes it. No schema change required.

**Alternatives considered**:
- **Add PURCHASE_IN as new type**: Would require ALTER TYPE on PostgreSQL ENUM — unnecessary since PURCHASE already exists and is semantically correct for goods receipt inbound movements

**Note**: The instruction-plan.md referenced `PURCHASE_IN` but codebase already has `PURCHASE`. All implementation should use `MovementType.PURCHASE`.

## Additional Findings

### Entity Type Choices (TenantFieldDefinition)
**Current**: PRODUCT, CUSTOMER, SUPPLIER, SALE_ORDER
**Action**: Add `PURCHASE_ORDER = "purchase_order"` to `EntityType` choices in `apps/core/models/customization.py`

### Permission Vocabulary (Role)
**Current VALID_MODULES**: `{"inventory", "sales", "purchases", "customers", "reports", "settings"}`
**Current VALID_ACTIONS**: `{"read", "write", "create", "delete", "admin"}`
**Action**: `purchases` and `reports` already exist. Need to add `export` to VALID_ACTIONS for `reports.export`. Module names use English (`purchases` not `compras`, `reports` not `reportes`).

### seed_all Chain
**Current**: `seed_data → seed_inventario → seed_ventas → seed_facturacion`
**Action**: Add `seed_compras` (after `seed_facturacion`, needs products) and `seed_reportes` (last)
