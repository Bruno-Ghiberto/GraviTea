# Quickstart: Backend Modules Solidification

**Branch**: `016-backend-modules-solidification`
**Prerequisite**: Branch checked out, Docker Compose running, existing tests passing

## Execution Sequence

### Phase 1: COMPRAS App + Supplier Migration (RISKIEST)
1. Create `backend/apps/compras/` app skeleton (apps.py, models, views, serializers, urls, admin)
2. Move Supplier model definition to `compras/models.py` (preserve all encrypted fields)
3. Create SeparateDatabaseAndState migration pair (compras add + inventario remove)
4. Update Product.supplier FK to reference `compras.Supplier`
5. Move SupplierViewSet + SupplierSerializer to compras
6. Update URL routing: register suppliers in compras urls, remove from inventario urls
7. Update TenantFieldDefinition — entity_type `supplier` still works (no change needed)
8. Update all test imports referencing `inventario.Supplier`
9. **GATE**: Full regression — 0 new failures

### Phase 2: PurchaseOrder + Items
1. Create PurchaseOrder model (state machine: DRAFT→CONFIRMED→PARTIAL_RECEIVED→RECEIVED→CANCELLED)
2. Create PurchaseOrderItem model (FK to PO + Product, quantity, unit_price)
3. Create serializers (nested items pattern from SaleOrder)
4. Create ViewSets (CRUD + confirm/cancel actions)
5. Register URLs under `/api/v1/compras/purchase-orders/`
6. Write unit + integration tests (60+ total for all compras phases)
7. **GATE**: Regression green

### Phase 3: GoodsReceipt + Stock Integration
1. Create GoodsReceipt + GoodsReceiptLine models
2. Create GoodsReceiptService (creates StockMovement type=PURCHASE per line)
3. Implement over-receipt rejection (received > ordered per line)
4. Auto-transition PO state based on cumulative receipt quantities
5. Create serializers + ViewSet (nested under PO or standalone)
6. Write tests (receipt, stock update, over-receipt, partial receipt, immutability)
7. **GATE**: Regression green

### Phase 4: JSONB Custom Fields
1. Add `purchase_order` to TenantFieldDefinition.EntityType choices
2. Add `custom_data` JSONField to PurchaseOrder (if not in Phase 2)
3. Apply CustomFieldsMixin to PurchaseOrderSerializer (set entity_type = "purchase_order")
4. Write tests (field definition, create with custom data, validation, merge on update)
5. **GATE**: Regression green

### Phase 5: REPORTES Skeleton
1. Create `backend/apps/reportes/` app skeleton
2. Create ReportDefinition, SavedReport, ExportJob models
3. Create serializers + ViewSets (basic CRUD, no generation logic)
4. Register URLs under `/api/v1/reportes/`
5. Create ReportService with read-only QuerySet methods for cross-module data
6. Write tests (15+ minimum: CRUD, tenant isolation, filters)
7. **GATE**: Regression green

### Phase 6: Permissions
1. Add `export` to VALID_ACTIONS in Role model (purchases/reports modules already exist)
2. Update compras ViewSets with permission enforcement
3. Update reportes ViewSets with permission enforcement
4. Update seed roles with new permission combinations
5. Write permission tests
6. **GATE**: Regression green

### Phase 7: Seed Data
1. Create `seed_compras` command (POs in various states, goods receipts)
2. Create `seed_reportes` command (sample ReportDefinitions)
3. Update seed_all chain: add seed_compras + seed_reportes
4. Write seed command tests (idempotent execution)
5. **GATE**: Regression green

### Phase 8: Final Validation
1. Full regression suite — 0 new failures
2. Generate OpenAPI YAML for compras + reportes
3. Verify: 60+ compras tests, 15+ reportes tests
4. Verify: coverage >= 78%
5. Review all cross-module FK references

## Key Files

| File | Purpose |
|------|---------|
| `specs/016-backend-modules-solidification/spec.md` | Feature specification |
| `specs/016-backend-modules-solidification/plan.md` | This implementation plan |
| `specs/016-backend-modules-solidification/research.md` | Research decisions |
| `specs/016-backend-modules-solidification/data-model.md` | Entity definitions + ERDs |
| `Docs/Temp-prompting/016/instruction-plan.md` | Plan phase context |
| `backend/apps/ventas/models.py` | SaleOrder pattern reference |
| `backend/apps/inventario/services.py` | StockService pattern reference |
| `backend/apps/core/serializers/customization.py` | CustomFieldsMixin reference |

## Test Execution

```bash
# Targeted tests (during development)
bash scripts/run-tests-external.sh "016-phase1" "backend/venv-wsl/bin/python -m pytest tests/compras/ --tb=short -q"

# Full regression (after each phase)
bash scripts/run-tests-external.sh "016-regression" "backend/venv-wsl/bin/python -m pytest tests/ --tb=short -q"

# Read results
cat Docs/Tests/016-regression.summary
```
